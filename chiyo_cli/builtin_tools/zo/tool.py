"""Framework-backed zo built-in."""

from chiyo_cli.builtin_tools.zo.attachments import attachment_path
from chiyo_cli.builtin_tools.zo.item import (
    filter_items,
    item_title,
    item_url,
    item_year,
    normalize_config,
    select_uri,
)
from chiyo_cli.builtin_tools.zo.local_api import load_items_from_local_api
from chiyo_cli.builtin_tools.zo.sqlite_source import load_sqlite_items
from chiyo_cli.output import print_warning
from chiyo_cli.toolkit import PickOpenTool, ToolError, open_location as toolkit_open_location


DEFAULT_CONFIG = {
    "local_api_url": "http://localhost:23119/api/",
    "zotero_data_dir": "~/Zotero",
    "fzf_prompt": "zo> ",
}


def warn(message):
    print_warning("zo", message)


def load_items(config, query, source, fail):
    config = normalize_config(config)

    if source in ("auto", "local-api"):
        try:
            return load_items_from_local_api(config, query)
        except RuntimeError as error:
            if source == "local-api":
                fail(str(error))

            warn("local API unavailable; using Zotero SQLite fallback.")

    return filter_items(load_sqlite_items(config, fail), query)


def open_location(location, fail):
    try:
        toolkit_open_location(location)
    except ToolError as error:
        fail(str(error))


class Tool(PickOpenTool):
    name = "Zotero Search"
    cmd = "zo"
    author = "Chiyo CLI"
    author_id = "chiyo"
    description = "Search Zotero items and open a selection."
    docs = """
    # zo

    Search Zotero items by title and open the selected Zotero item, URL, or
    local PDF attachment.
    """
    prompt = "zo> "
    default_config = DEFAULT_CONFIG
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
        return load_items(
            config,
            getattr(self, "_query", ""),
            getattr(self, "_source", "auto"),
            self.fail,
        )

    def match(self, item, query, config):
        return item in filter_items([item], query)

    def display_fields(self, item, config):
        return [
            self.primary(item_title(item)),
            self.secondary(item.get("creators", "")),
            self.plain(item_year(item)),
        ]

    def completion_items(self, config):
        self._query = ""
        self._source = "auto"
        return self.items(config)

    def completion_label(self, item, config):
        return item_title(item)

    def open_item(self, item, args, config):
        if args.print_key:
            print(item["key"])
            return item["key"]

        if args.print_url:
            url = item_url(item)

            if not url:
                self.fail("selected item has no URL or DOI.")

            print(url)
            return url

        if args.print_path or args.open_pdf:
            path = attachment_path(config, item)

            if not path:
                self.fail("selected item has no local PDF attachment.")

            if args.print_path:
                print(path)
                return path

            open_location(path, self.fail)
            return path

        location = select_uri(item)
        open_location(location, self.fail)
        return location
