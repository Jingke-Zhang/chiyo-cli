"""Zotero SQLite fallback loading helpers."""

import os
import shutil
import sqlite3
import tempfile

from chiyo_cli.paths import expand_path
from chiyo_cli.tool_config import TOOLS_CONFIG_PATH


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
