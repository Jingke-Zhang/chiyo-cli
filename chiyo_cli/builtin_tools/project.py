"""Framework-backed proj built-in."""

import re
from pathlib import Path

from chiyo_cli.fzf import display_width
from chiyo_cli.output import print_warning
from chiyo_cli.paths import compact_path, existing_dirs
from chiyo_cli.toolkit import (
    Field,
    PickOpenTool,
    STYLE_PRIMARY,
    STYLE_SECONDARY,
    ToolError,
    require_command,
    run_command,
)


DEFAULT_CONFIG = {
    "roots": ["~/Documents", "~/Projects", "~/Developer"],
    "markers": [".project", ".git"],
    "exclude": ["node_modules", "Library", ".cache"],
    "fzf_prompt": "proj> ",
}


def warn(message):
    print_warning("proj", message)


def require_fd(fail):
    try:
        require_command("fd")
    except ToolError as error:
        fail(str(error))


def normalize_roots(roots, fail=None):
    return existing_dirs(roots, "project root", warn, fail)


def escape_fd_alternative(value):
    return re.escape(value)


def marker_pattern(markers):
    alternatives = [escape_fd_alternative(marker) for marker in markers]

    if len(alternatives) == 1:
        return f"^{alternatives[0]}$"

    return "^(" + "|".join(alternatives) + ")$"


def fd_command(roots, markers, exclude=None, max_results=None):
    command = ["fd", "--absolute-path", "--hidden"]
    exclude = exclude or []

    for pattern_to_exclude in exclude:
        command.extend(["--exclude", pattern_to_exclude])

    if max_results is not None:
        command.append(f"--max-results={max_results}")

    return [*command, marker_pattern(markers), *roots]


def run_fd(roots, markers, exclude=None, max_results=None, fail=None):
    fail = fail or (lambda message: (_ for _ in ()).throw(RuntimeError(message)))
    try:
        result = run_command(
            fd_command(roots, markers, exclude, max_results),
            "fd failed while searching projects",
        )
    except ToolError as error:
        fail(str(error))

    return result.stdout.splitlines()


def project_from_marker(path):
    return str(Path(path.rstrip("/")).parent)


def project_name(path):
    return Path(path.rstrip("/")).name


def unique_paths(paths):
    seen = set()
    unique = []

    for path in paths:
        if not path or path in seen:
            continue

        seen.add(path)
        unique.append(path)

    return unique


def all_projects(roots, markers, exclude, fail, max_results=None):
    marker_paths = run_fd(roots, markers, exclude, max_results, fail)
    projects = [project_from_marker(path) for path in marker_paths]
    return unique_paths(projects)


def filter_projects(projects, query):
    if not query:
        return projects

    query = query.lower()

    return [
        path
        for path in projects
        if query in project_name(path).lower()
    ]


def project_widths(projects):
    return [
        max((display_width(project_name(path)) for path in projects), default=0),
    ]


def project_fields(path, widths):
    name_padding = " " * (widths[0] - display_width(project_name(path)) + 2)
    return [
        Field(project_name(path) + name_padding, STYLE_PRIMARY),
        Field(compact_path(path), STYLE_SECONDARY),
    ]


class Tool(PickOpenTool):
    name = "Project"
    cmd = "proj"
    author = "Chiyo CLI"
    author_id = "shiori-route"
    description = "Select a project directory for cd."
    shell = True
    docs = """
    # proj

    Select a project directory by marker files and emit a shell action that can
    change the parent shell's current directory.
    """
    prompt = "proj> "
    default_config = DEFAULT_CONFIG
    search_display_fields = [1]

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

    def query_from_args(self, args):
        self._root_args = args.root
        self._exclude_args = args.exclude or []
        return super().query_from_args(args)

    def normalize_config(self, config):
        roots = self._root_args if self._root_args else config["roots"]
        normalized = dict(config)
        normalized["roots"] = normalize_roots(roots, self.fail)
        normalized["exclude"] = list(config["exclude"]) + self._exclude_args
        return normalized

    def items(self, config):
        config = self.normalize_config(config)
        return all_projects(
            config["roots"],
            config["markers"],
            config["exclude"],
            self.fail,
        )

    def match(self, item, query, config):
        return item in filter_projects([item], query)

    def display_fields(self, item, config):
        return [
            self.primary(project_name(item)),
            self.secondary(compact_path(item)),
        ]

    def completion_label(self, item, config):
        return project_name(item)

    def select_item(self, items, query, args, config):
        if query and not args.confirm and len(items) == 1:
            return items[0]

        widths = project_widths(items)
        rows_by_item = {path: project_fields(path, widths) for path in items}
        return self.choose_with_rows(items, rows_by_item, config)

    def choose_with_rows(self, items, rows_by_item, config):
        from chiyo_cli.fzf import choose_item

        return choose_item(
            items,
            [rows_by_item[path] for path in items],
            self.prompt_value(config),
            "a project",
            self.fail,
            search_display_fields=[1],
        )

    def open_item(self, item, args, config):
        return self.cd(item)
