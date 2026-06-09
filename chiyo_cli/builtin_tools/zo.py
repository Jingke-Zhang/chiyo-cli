"""Framework-backed zo built-in."""

from chiyo_cli.builtin_tools.legacy import load_legacy_command
from chiyo_cli.toolkit import PickOpenTool


LEGACY = load_legacy_command("zo")


class Tool(PickOpenTool):
    name = "Zotero Search"
    command = "zo"
    author = "Chiyo CLI"
    description = "Search Zotero items and open a selection."
    docs = """
    # zo

    Search Zotero items by title and open the selected Zotero item, URL, or
    local PDF attachment.
    """
    prompt = "zo> "
    default_config = LEGACY.DEFAULT_CONFIG
    search_display_fields = [1]

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            choices=["auto", "local-api", "sqlite"],
            default="auto",
            help="Choose Zotero data source. Default: auto.",
        )
        parser.add_argument(
            "--open-pdf",
            action="store_true",
            help="Open the selected item's first local PDF attachment.",
        )
        parser.add_argument(
            "--print-key",
            action="store_true",
            help="Print the selected Zotero item key instead of opening it.",
        )
        parser.add_argument(
            "--print-url",
            action="store_true",
            help="Print the selected item's URL, or DOI URL, instead of opening it.",
        )
        parser.add_argument(
            "--print-path",
            action="store_true",
            help="Print the selected item's first local PDF attachment path.",
        )

    def query_from_args(self, args):
        self._query = super().query_from_args(args)
        self._source = args.source
        return self._query

    def items(self, config):
        return LEGACY.load_items(
            config,
            getattr(self, "_query", ""),
            getattr(self, "_source", "auto"),
        )

    def match(self, item, query, config):
        return item in LEGACY.filter_items([item], query)

    def display_fields(self, item, config):
        return [
            LEGACY.Field(LEGACY.item_title(item), LEGACY.STYLE_PRIMARY),
            LEGACY.Field(item.get("creators", ""), LEGACY.STYLE_SECONDARY),
            LEGACY.Field(LEGACY.item_year(item)),
        ]

    def completion_items(self, config):
        self._query = ""
        self._source = "auto"
        return self.items(config)

    def completion_label(self, item, config):
        return LEGACY.item_title(item)

    def select_item(self, items, query, args, config):
        return LEGACY.select_item(items, config, bool(query) and not args.confirm)

    def open_item(self, item, args, config):
        if args.print_key:
            print(item["key"])
            return item["key"]

        if args.print_url:
            url = LEGACY.item_url(item)

            if not url:
                self.fail("selected item has no URL or DOI.")

            print(url)
            return url

        if args.print_path or args.open_pdf:
            path = LEGACY.attachment_path(config, item)

            if not path:
                self.fail("selected item has no local PDF attachment.")

            if args.print_path:
                print(path)
                return path

            LEGACY.open_location(path)
            return path

        location = LEGACY.select_uri(item)
        LEGACY.open_location(location)
        return location
