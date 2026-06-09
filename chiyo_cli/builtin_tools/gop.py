"""Framework-backed gop built-in."""

import os
import sys

from chiyo_cli.builtin_tools.legacy import load_legacy_command
from chiyo_cli.toolkit import PickOpenTool, ShellAction


LEGACY = load_legacy_command("gop-select")


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
    default_config = LEGACY.DEFAULT_CONFIG

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
        return LEGACY.path_fields(item)

    def query_from_args(self, args):
        return " ".join(args.query)

    def roots_from_args(self, args, config):
        return LEGACY.normalize_roots(args.root) if args.root else config["roots"]

    def exclude_from_args(self, args, config):
        return config["exclude"] + (args.exclude or [])

    def print_completions_for_args(self, args, config):
        LEGACY.list_completions(
            self.query_from_args(args),
            self.roots_from_args(args, config),
            self.exclude_from_args(args, config),
        )

    def select_path(self, args, config):
        query = self.query_from_args(args)
        roots = self.roots_from_args(args, config)
        exclude = self.exclude_from_args(args, config)

        if query and not args.confirm:
            paths = LEGACY.unique_paths(
                LEGACY.run_fd(query, roots, exclude, max_results=2)
            )

            if not paths:
                self.fail("no paths found.")

            if len(paths) == 1:
                return paths[0]

            return LEGACY.choose_path_stream(query, roots, exclude, config)

        return LEGACY.choose_path_stream(query, roots, exclude, config)

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
        if os.path.isdir(item):
            return ShellAction.cd(item)

        return ShellAction.open(item)
