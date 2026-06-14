"""Zotero item normalization and display helpers."""


def normalize_config(config):
    from chiyo_cli.paths import expand_path

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
