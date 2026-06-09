"""Framework-backed proj built-in."""

from chiyo_cli.builtin_tools.legacy import load_legacy_command
from chiyo_cli.toolkit import PickOpenTool, ShellAction


LEGACY = load_legacy_command("proj-select")


class Tool(PickOpenTool):
    name = "Project Switcher"
    command = "proj"
    author = "Chiyo CLI"
    description = "Select a project directory for cd."
    docs = """
    # proj

    Select a project directory by marker files and emit a shell action that can
    change the parent shell's current directory.
    """
    prompt = "proj> "
    default_config = LEGACY.DEFAULT_CONFIG
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

    def items(self, config):
        roots = LEGACY.normalize_roots(
            self._root_args
            if self._root_args
            else config["roots"]
        )
        exclude = config["exclude"] + self._exclude_args
        return LEGACY.all_projects(roots, config["markers"], exclude)

    def match(self, item, query, config):
        return item in LEGACY.filter_projects([item], query)

    def display_fields(self, item, config):
        return [
            LEGACY.Field(LEGACY.project_name(item), LEGACY.STYLE_PRIMARY),
            LEGACY.Field(LEGACY.compact_path(item), LEGACY.STYLE_SECONDARY),
        ]

    def completion_label(self, item, config):
        return LEGACY.project_name(item)

    def select_item(self, items, query, args, config):
        return LEGACY.select_project(items, config, bool(query) and not args.confirm)

    def open_item(self, item, args, config):
        return ShellAction.cd(item)
