"""Zotero attachment resolution helpers."""

from urllib.error import URLError
from urllib.parse import unquote, urlparse
from urllib.request import urlopen

from chiyo_cli.builtin_tools.zo.item import normalize_config
from chiyo_cli.builtin_tools.zo.local_api import local_api_get_json


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
