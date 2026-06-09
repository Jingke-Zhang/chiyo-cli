"""Framework-backed app built-in."""

import sys

from chiyo_cli.builtin_tools.legacy import load_legacy_command
from chiyo_cli.toolkit import PickOpenTool


LEGACY = load_legacy_command("app")


class Tool(PickOpenTool):
    name = "Application Launcher"
    command = "app"
    author = "Chiyo CLI"
    description = "Search installed macOS applications."
    docs = """
    # app

    Search installed macOS applications, resolve configured aliases, and launch
    the selected application.
    """
    prompt = "app> "
    default_config = LEGACY.DEFAULT_CONFIG
    search_display_fields = [1, 2]

    def add_arguments(self, parser):
        parser.add_argument(
            "--print-name",
            action="store_true",
            help="Print the selected application name instead of opening it.",
        )

    def items(self, config):
        return LEGACY.discover_apps()

    def match(self, item, query, config):
        return item in LEGACY.filter_apps([item], query, config.get("alias", {}))

    def display_fields(self, item, config):
        alias = LEGACY.alias_for_app(item["name"], config.get("alias", {}))
        return LEGACY.app_fields(item, alias)

    def completion_items(self, config):
        return self.items(config)

    def completion_label(self, item, config):
        return item["name"]

    def select_item(self, items, query, args, config):
        return LEGACY.select_app(items, config, bool(query) and not args.confirm)

    def run(self, argv=None, config=None):
        config = dict(self.default_config if config is None else config)
        args = self.parser().parse_args(argv if argv is not None else sys.argv[1:])

        if args.list_completions:
            self.print_completions(config)
            return None

        query = self.query_from_args(args)
        alias_target = LEGACY.resolve_alias(query, config.get("alias", {}))

        if alias_target and not args.confirm:
            selected = {
                "name": alias_target,
                "path": None,
            }
            return self.open_item(selected, args, config)

        return super().run(argv=argv, config=config)

    def open_item(self, item, args, config):
        if args.print_name:
            print(item["name"])
            return item["name"]

        LEGACY.open_app(item)
        return item
