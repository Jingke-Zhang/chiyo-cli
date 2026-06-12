"""Framework-backed gop built-in."""

import re
import subprocess
import sys
from pathlib import Path

from chiyo_cli.fzf import Field, choose_item, field_widths, format_row
from chiyo_cli.output import print_warning
from chiyo_cli.paths import compact_path, existing_dirs
from chiyo_cli.toolkit import PickOpenTool, ToolError, require_command, run_command


STYLE_DIR = "\033[1;34m"
STYLE_FILE = ""
STYLE_EXECUTABLE = "\033[1;32m"
ANSI_PATTERN = re.compile(r"\033\[[0-9;]*m")
DEFAULT_CONFIG = {
    "roots": ["~/Documents", "~/Downloads", "~/Desktop"],
    "exclude": ["Library", "node_modules", "OrbStack"],
    "fzf_prompt": "gop> ",
}


def warn(message):
    print_warning("gop", message)


def normalize_roots(roots, fail=None):
    return existing_dirs(roots, "search root", warn, fail)


def fd_command(query, roots, exclude=None, max_results=None):
    pattern = query or "."
    command = ["fd", "--absolute-path"]
    exclude = exclude or []

    for pattern_to_exclude in exclude:
        command.extend(["--exclude", pattern_to_exclude])

    if max_results is not None:
        command.append(f"--max-results={max_results}")

    return [*command, pattern, *roots]


def require_fd(fail):
    try:
        require_command("fd")
    except ToolError as error:
        fail(str(error))


def require_fzf(fail):
    try:
        require_command("fzf")
    except ToolError as error:
        fail(str(error))


def run_fd(query, roots, exclude=None, max_results=None, fail=None):
    fail = fail or (lambda message: (_ for _ in ()).throw(RuntimeError(message)))
    try:
        result = run_command(
            fd_command(query, roots, exclude, max_results),
            "fd failed while searching paths",
        )
    except ToolError as error:
        fail(str(error))

    return result.stdout.splitlines()


def path_kind(path):
    path = Path(path)

    if path.is_dir():
        return "dir"

    if path.exists() and path.stat().st_mode & 0o111:
        return "exec"

    return "file"


def style_for_kind(kind):
    if kind == "dir":
        return STYLE_DIR

    if kind == "exec":
        return STYLE_EXECUTABLE

    return STYLE_FILE


def path_fields(path):
    return [Field(compact_path(path), style_for_kind(path_kind(path)))]


def path_filter_fields(path):
    return [compact_path(path), path]


def format_path_choice(path):
    fields = path_fields(path)
    return format_row(0, fields, field_widths([fields]), path_filter_fields(path))


def parse_choice(choice):
    if "\t" not in choice:
        return choice

    without_index = choice.rsplit("\t#", 1)[0]
    return ANSI_PATTERN.sub("", without_index.rsplit("\t", 1)[1])


def unique_paths(paths):
    seen = set()
    unique = []

    for path in paths:
        if not path or path in seen:
            continue

        seen.add(path)
        unique.append(path)

    return unique


def choose_path(paths, config, fail):
    rows = [path_fields(path) for path in paths]
    filter_rows = [path_filter_fields(path) for path in paths]
    return choose_item(
        paths,
        rows,
        config["fzf_prompt"],
        "a path",
        fail,
        filter_rows=filter_rows,
    )


def choose_path_stream(query, roots, exclude, config, fail):
    require_fd(fail)
    require_fzf(fail)
    fd_process = subprocess.Popen(
        fd_command(query, roots, exclude),
        stdout=subprocess.PIPE,
        text=True,
    )

    fzf_process = subprocess.Popen(
        [
            "fzf",
            f"--prompt={config['fzf_prompt']}",
            "--ansi",
            "--with-nth=1",
            "--nth=1",
            "--delimiter=\t",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        if fd_process.stdout is not None and fzf_process.stdin is not None:
            for path in fd_process.stdout:
                path = path.rstrip("\n")

                if not path:
                    continue

                try:
                    fzf_process.stdin.write(format_path_choice(path) + "\n")
                except BrokenPipeError:
                    break

        if fzf_process.stdin is not None:
            fzf_process.stdin.close()

        stdout = fzf_process.stdout.read() if fzf_process.stdout is not None else ""
        if fzf_process.stderr is not None:
            fzf_process.stderr.read()
        returncode = fzf_process.wait()
    finally:
        if fd_process.stdout is not None:
            fd_process.stdout.close()

        fd_process.wait()

    if returncode == 130:
        return None

    if returncode != 0:
        fail("fzf failed while selecting a path.")

    selected = stdout.strip()

    if not selected:
        return None

    return parse_choice(selected)


class Tool(PickOpenTool):
    name = "Go Path"
    command = "gop"
    author = "Chiyo CLI"
    description = "Select a path for cd or open."
    docs = """
    # gop

    Select a file or directory. Directories emit a shell action that can change
    the parent shell's current directory; files emit an open action.
    """
    prompt = "gop> "
    default_config = DEFAULT_CONFIG

    def add_arguments(self, parser):
        parser.add_argument(
            "-r",
            "--root",
            action="append",
            help="Search this directory instead of configured roots. Can be used more than once.",
        )
        parser.add_argument(
            "-E",
            "--exclude",
            action="append",
            help="Exclude a glob pattern from fd search. Can be used more than once.",
        )

    def parser(self):
        parser = super().parser()
        parser.set_defaults(selected_path=None)
        return parser

    def items(self, config):
        return []

    def display_fields(self, item, config):
        return path_fields(item)

    def query_from_args(self, args):
        return " ".join(args.query)

    def roots_from_args(self, args, config):
        roots = args.root if args.root else config["roots"]
        return self.existing_dirs(roots, "search root")

    def exclude_from_args(self, args, config):
        return config["exclude"] + (args.exclude or [])

    def print_completions_for_args(self, args, config):
        query = self.query_from_args(args)
        roots = self.roots_from_args(args, config)
        exclude = self.exclude_from_args(args, config)

        for path in unique_paths(
            run_fd(query, roots, exclude, max_results=200, fail=self.fail)
        ):
            print(compact_path(path))

    def select_path(self, args, config):
        query = self.query_from_args(args)
        roots = self.roots_from_args(args, config)
        exclude = self.exclude_from_args(args, config)

        if query and not args.confirm:
            paths = unique_paths(
                run_fd(query, roots, exclude, max_results=2, fail=self.fail)
            )

            if not paths:
                self.fail("no paths found.")

            if len(paths) == 1:
                return paths[0]

            return choose_path_stream(query, roots, exclude, config, self.fail)

        return choose_path_stream(query, roots, exclude, config, self.fail)

    def run(self, argv=None, config=None, execute_shell_actions=True):
        config = dict(self.default_config if config is None else config)
        args = self.parser().parse_args(argv if argv is not None else sys.argv[1:])

        if args.list_completions:
            self.print_completions_for_args(args, config)
            return None

        selected = self.select_path(args, config)

        if not selected:
            return None

        result = self.open_item(selected, args, config)

        if execute_shell_actions:
            return result.execute()

        return result

    def open_item(self, item, args, config):
        if Path(item).is_dir():
            return self.cd(item)

        return self.open(item)
