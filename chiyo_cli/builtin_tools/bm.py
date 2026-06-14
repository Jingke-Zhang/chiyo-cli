"""Framework-backed bm built-in."""

import plistlib

from chiyo_cli.paths import expand_path
from chiyo_cli.tool_config import TOOLS_CONFIG_PATH
from chiyo_cli.toolkit import PickOpenTool


DEFAULT_CONFIG = {
    "bookmarks_path": "~/Library/Safari/Bookmarks.plist",
    "skip_folders": [
        "Bookmarks",
        "BookmarksMenu",
        "Tab Group Favorites",
        "com.apple.ReadingList",
        "Reading List",
    ],
    "fzf_prompt": "bm> ",
    "browser": "Safari",
}


def get_node_name(node):
    uri_dict = node.get("URIDictionary")

    if isinstance(uri_dict, dict):
        title = uri_dict.get("title")

        if title:
            return title

    return node.get("Title") or node.get("WebBookmarkTitle")


def normalize_path(parts, skip_folders, rename_folders):
    normalized = []

    for part in parts:
        if not part or part in skip_folders:
            continue

        normalized.append(rename_folders.get(part, part))

    return normalized


def walk_bookmarks(node, path, results, config):
    name = get_node_name(node)

    if name:
        path = path + [name]

    if "URLString" in node:
        normalized_path = normalize_path(
            path,
            config["skip_folders"],
            config["rename_folders"],
        )

        if normalized_path:
            results.append(("/".join(normalized_path), node["URLString"]))

        return

    for child in node.get("Children", []):
        walk_bookmarks(child, path, results, config)


def load_bookmarks(config, fail):
    bookmarks_path = config["bookmarks_path"]

    if not bookmarks_path.exists():
        fail(
            f"bookmark file not found: {bookmarks_path}\n"
            f"Run 'chiyo config init bm --append' and edit bookmarks_path in "
            f"{expand_path(TOOLS_CONFIG_PATH)} "
            "if your bookmarks live somewhere else."
        )

    with bookmarks_path.open("rb") as file:
        data = plistlib.load(file)

    results = []
    walk_bookmarks(data, [], results, config)

    seen = set()
    unique_results = []

    for display_name, url in results:
        key = (display_name, url)

        if key in seen:
            continue

        seen.add(key)
        unique_results.append((display_name, url))

    return unique_results


class Tool(PickOpenTool):
    name = "Browser Bookmarks"
    cmd = "bm"
    author = "Chiyo CLI"
    author_id = "chiyo"
    description = "Search browser bookmarks and open a URL."
    docs = """
    # bm

    Search normalized bookmark paths and open the selected URL with the
    configured browser.
    """
    prompt = "bm> "
    default_config = DEFAULT_CONFIG
    search_display_fields = [1]

    def normalize_config(self, config):
        normalized = dict(config)
        normalized["bookmarks_path"] = self.path(normalized["bookmarks_path"])
        normalized["skip_folders"] = set(normalized.get("skip_folders", []))
        normalized["rename_folders"] = normalized.get("rename_folders", {})
        return normalized

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
        return load_bookmarks(self.normalize_config(config), self.fail)

    def match(self, item, query, config):
        if not query:
            return True

        display_name, _url = item
        return query.lower() in display_name.lower()

    def display_fields(self, item, config):
        display_name, url = item
        return [
            self.primary(display_name),
            self.secondary(url),
        ]

    def completion_label(self, item, config):
        display_name, _url = item
        return display_name

    def open_item(self, item, args, config):
        _display_name, url = item

        if args.print_url:
            return self.print(url)

        browser = args.browser or config["browser"]
        return self.open_with_app(url, browser)
