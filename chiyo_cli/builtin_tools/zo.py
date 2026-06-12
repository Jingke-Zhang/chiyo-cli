"""Framework-backed zo built-in."""

import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlparse
from urllib.request import urlopen

from chiyo_cli.output import print_warning
from chiyo_cli.paths import expand_path
from chiyo_cli.tool_config import TOOLS_CONFIG_PATH
from chiyo_cli.toolkit import Field, PickOpenTool, STYLE_PRIMARY, STYLE_SECONDARY


DEFAULT_CONFIG = {
    "local_api_url": "http://localhost:23119/api/",
    "zotero_data_dir": "~/Zotero",
    "fzf_prompt": "zo> ",
}


def warn(message):
    print_warning("zo", message)


def normalize_config(config):
    normalized = dict(config)
    normalized["zotero_data_dir"] = expand_path(normalized["zotero_data_dir"])
    normalized["local_api_url"] = normalized["local_api_url"].rstrip("/") + "/"
    return normalized


def item_title(item):
    return item.get("title") or "(untitled)"


def item_year(item):
    date = item.get("date") or ""
    return date[:4] if len(date) >= 4 and date[:4].isdigit() else ""


def creator_name(creator):
    if creator.get("name"):
        return creator["name"]

    return " ".join(
        part
        for part in [creator.get("firstName", ""), creator.get("lastName", "")]
        if part
    ).strip()


def format_creators(creators):
    names = [name for name in (creator_name(creator) for creator in creators) if name]

    if len(names) > 3:
        return ", ".join(names[:3]) + " et al."

    return ", ".join(names)


def doi_url(item):
    doi = item.get("doi") or ""

    if not doi:
        return ""

    return "https://doi.org/" + doi


def item_url(item):
    return item.get("url") or doi_url(item)


def select_uri(item):
    if item.get("library_type") == "group" and item.get("group_id"):
        return f"zotero://select/groups/{item['group_id']}/items/{item['key']}"

    return f"zotero://select/library/items/{item['key']}"


def local_api_get_json(config, path, params=None):
    params = params or {}
    query = ""

    if params:
        query = "?" + "&".join(
            f"{quote(str(key))}={quote(str(value))}"
            for key, value in params.items()
            if value is not None
        )

    url = config["local_api_url"] + path.lstrip("/") + query

    try:
        with urlopen(url, timeout=1.5) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise RuntimeError(f"local API returned HTTP {error.code}") from error
    except (OSError, URLError, json.JSONDecodeError) as error:
        raise RuntimeError("local API is unavailable") from error


def parse_local_api_item(entry):
    data = entry.get("data", {})
    library = entry.get("library", {})

    return {
        "key": data.get("key") or entry.get("key"),
        "library_id": library.get("id"),
        "library_type": library.get("type", "user"),
        "group_id": library.get("id") if library.get("type") == "group" else None,
        "item_type": data.get("itemType", ""),
        "title": data.get("title", ""),
        "creators": format_creators(data.get("creators", [])),
        "date": data.get("date", ""),
        "publication": data.get("publicationTitle", ""),
        "doi": data.get("DOI", ""),
        "url": data.get("url", ""),
        "attachment_path": "",
        "source": "local-api",
    }


def load_items_from_local_api(config, query):
    params = {
        "format": "json",
        "itemType": "-attachment",
    }

    entries = local_api_get_json(config, "users/0/items", params)
    items = []

    for entry in entries:
        item = parse_local_api_item(entry)

        if not item.get("key"):
            continue

        if item.get("item_type") in ("note", "annotation"):
            continue

        items.append(item)

    return filter_items(items, query)


def sqlite_path(config):
    return os.path.join(config["zotero_data_dir"], "zotero.sqlite")


def sqlite_snapshot(path, fail):
    if not os.path.exists(path):
        fail(
            f"Zotero database not found: {path}\n"
            f"Run 'chiyo config init zo --append' and edit zotero_data_dir in "
            f"{expand_path(TOOLS_CONFIG_PATH)} if your Zotero data lives somewhere else."
        )

    temp = tempfile.NamedTemporaryFile(prefix="chiyo-zotero-", suffix=".sqlite", delete=False)
    temp.close()
    shutil.copy2(path, temp.name)
    return temp.name


def query_rows(connection, sql):
    connection.row_factory = sqlite3.Row
    return [dict(row) for row in connection.execute(sql)]


def normalize_sqlite_attachment_path(config, attachment_key, path):
    if not path:
        return ""

    if path.startswith("storage:"):
        filename = path.split(":", 1)[1]
        return os.path.join(config["zotero_data_dir"], "storage", attachment_key, filename)

    return expand_path(path)


def load_sqlite_items(config, fail):
    snapshot = sqlite_snapshot(sqlite_path(config), fail)
    connection = None

    try:
        connection = sqlite3.connect(f"file:{snapshot}?mode=ro", uri=True)
        item_rows = query_rows(
            connection,
            """
            select
              i.itemID,
              i.key,
              i.libraryID,
              l.type as library_type,
              g.groupID as group_id,
              it.typeName as item_type,
              max(case when f.fieldName = 'title' then v.value end) as title,
              max(case when f.fieldName = 'date' then v.value end) as date,
              max(case when f.fieldName = 'publicationTitle' then v.value end) as publication,
              max(case when f.fieldName = 'DOI' then v.value end) as doi,
              max(case when f.fieldName = 'url' then v.value end) as url
            from items i
            join itemTypes it on it.itemTypeID = i.itemTypeID
            join libraries l on l.libraryID = i.libraryID
            left join groups g on g.libraryID = i.libraryID
            left join itemData d on d.itemID = i.itemID
            left join fields f on f.fieldID = d.fieldID
            left join itemDataValues v on v.valueID = d.valueID
            where it.typeName not in ('attachment', 'note', 'annotation')
              and not exists (
                select 1 from deletedItems di where di.itemID = i.itemID
              )
            group by i.itemID
            order by lower(coalesce(title, '')), i.itemID
            """,
        )
        creator_rows = query_rows(
            connection,
            """
            select itemID, firstName, lastName, fieldMode
            from (
              select
                ic.itemID,
                c.firstName,
                c.lastName,
                c.fieldMode,
                ic.orderIndex
              from itemCreators ic
              join creators c on c.creatorID = ic.creatorID
              order by ic.itemID, ic.orderIndex
            )
            """,
        )
        attachment_rows = query_rows(
            connection,
            """
            select
              ia.parentItemID as parent_item_id,
              ai.key as attachment_key,
              ia.path
            from itemAttachments ia
            join items ai on ai.itemID = ia.itemID
            where ia.parentItemID is not null
              and ia.contentType = 'application/pdf'
            order by ia.parentItemID, ia.itemID
            """,
        )
    finally:
        if connection is not None:
            connection.close()
        os.unlink(snapshot)

    creators_by_item = {}

    for row in creator_rows:
        if row.get("fieldMode") == 1:
            name = row.get("lastName") or ""
        else:
            name = " ".join(
                part for part in [row.get("firstName"), row.get("lastName")] if part
            ).strip()

        if name:
            creators_by_item.setdefault(row["itemID"], []).append(name)

    attachment_by_item = {}

    for row in attachment_rows:
        if row["parent_item_id"] in attachment_by_item:
            continue

        attachment_by_item[row["parent_item_id"]] = normalize_sqlite_attachment_path(
            config,
            row["attachment_key"],
            row["path"],
        )

    items = []

    for row in item_rows:
        names = creators_by_item.get(row["itemID"], [])
        creators = ", ".join(names[:3])

        if len(names) > 3:
            creators += " et al."

        items.append(
            {
                "key": row["key"],
                "library_id": row["libraryID"],
                "library_type": row["library_type"],
                "group_id": row["group_id"],
                "item_type": row["item_type"] or "",
                "title": row["title"] or "",
                "creators": creators,
                "date": row["date"] or "",
                "publication": row["publication"] or "",
                "doi": row["doi"] or "",
                "url": row["url"] or "",
                "attachment_path": attachment_by_item.get(row["itemID"], ""),
                "source": "sqlite",
            }
        )

    return items


def searchable_title(item):
    return item.get("title", "").lower()


def filter_items(items, query):
    if not query:
        return items

    terms = query.lower().split()

    return [
        item
        for item in items
        if all(term in searchable_title(item) for term in terms)
    ]


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


def local_api_file_url(config, item):
    children = local_api_get_json(
        config,
        f"users/0/items/{item['key']}/children",
        {"format": "json", "itemType": "attachment"},
    )

    for child in children:
        data = child.get("data", {})

        if data.get("contentType") != "application/pdf":
            continue

        attachment_key = data.get("key") or child.get("key")
        url = config["local_api_url"] + f"users/0/items/{attachment_key}/file/view/url"

        with urlopen(url, timeout=1.5) as response:
            return response.read().decode("utf-8").strip()

    return ""


def file_url_to_path(url):
    parsed = urlparse(url)

    if parsed.scheme == "file":
        return unquote(parsed.path)

    return url


def attachment_path(config, item):
    config = normalize_config(config)

    if item.get("attachment_path"):
        return item["attachment_path"]

    if item.get("source") != "local-api":
        return ""

    try:
        return file_url_to_path(local_api_file_url(config, item))
    except (RuntimeError, OSError, URLError):
        return ""


def open_location(location, fail):
    if shutil.which("open") is None:
        fail("macOS 'open' command is not available.")

    result = subprocess.run(
        ["open", expand_path(location)],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        detail = result.stderr.strip() or "unknown error"
        fail(f"could not open {location}: {detail}")


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
            Field(item_title(item), STYLE_PRIMARY),
            Field(item.get("creators", ""), STYLE_SECONDARY),
            Field(item_year(item)),
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
