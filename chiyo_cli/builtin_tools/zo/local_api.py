"""Zotero Local API loading helpers."""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen

from chiyo_cli.builtin_tools.zo.item import filter_items, format_creators


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
