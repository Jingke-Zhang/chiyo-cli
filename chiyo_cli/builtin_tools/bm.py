"""Framework-backed bm built-in."""

from chiyo_cli.builtin_tools.legacy import load_legacy_command
from chiyo_cli.toolkit import PickOpenTool, ShellAction


LEGACY = load_legacy_command("bm")


class Tool(PickOpenTool):
    name = "Bookmarks"
    command = "bm"
    author = "Chiyo CLI"
    description = "Search browser bookmarks and open a URL."
    docs = """
    # bm

    Search normalized bookmark paths and open the selected URL with the
    configured browser.
    """
    prompt = "bm> "
    default_config = LEGACY.DEFAULT_CONFIG
    search_display_fields = [1]

    def add_arguments(self, parser):
        parser.add_argument(
            "--print-url",
            action="store_true",
            help="Print the selected URL instead of opening it.",
        )
        parser.add_argument(
            "--browser",
            help="Override the configured browser for this run.",
        )

    def items(self, config):
        return LEGACY.load_bookmarks(config)

    def match(self, item, query, config):
        return item in LEGACY.filter_bookmarks([item], query)

    def display_fields(self, item, config):
        display_name, url = item
        return [
            LEGACY.Field(display_name, LEGACY.STYLE_PRIMARY),
            LEGACY.Field(url, LEGACY.STYLE_SECONDARY),
        ]

    def completion_label(self, item, config):
        display_name, _url = item
        return display_name

    def select_item(self, items, query, args, config):
        selected_url = LEGACY.select_bookmark(
            items,
            config,
            bool(query) and not args.confirm,
        )

        if selected_url is None:
            return None

        return next(item for item in items if item[1] == selected_url)

    def open_item(self, item, args, config):
        _display_name, url = item

        if args.print_url:
            return ShellAction.print(url)

        browser = args.browser or config["browser"]
        LEGACY.open_url(url, browser)
        return url
