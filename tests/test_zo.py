import json
import os
import sqlite3
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock

from chiyo_cli.builtin_tools import zo as ZO


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.data


def api_item(key="ABC12345", title="Introduction to Online Convex Optimization"):
    return {
        "key": key,
        "library": {"type": "user", "id": 1},
        "data": {
            "key": key,
            "itemType": "journalArticle",
            "title": title,
            "creators": [{"firstName": "Elad", "lastName": "Hazan"}],
            "date": "2024-00-00",
            "publicationTitle": "Lecture Notes",
            "DOI": "10.1000/example",
            "url": "",
        },
    }


def create_sqlite_fixture(path):
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        create table items (itemID integer primary key, key text, itemTypeID integer, libraryID integer);
        create table itemTypes (itemTypeID integer primary key, typeName text);
        create table libraries (libraryID integer primary key, type text);
        create table groups (groupID integer primary key, libraryID integer, name text);
        create table fields (fieldID integer primary key, fieldName text);
        create table itemData (itemID integer, fieldID integer, valueID integer);
        create table itemDataValues (valueID integer primary key, value text);
        create table deletedItems (itemID integer);
        create table creators (creatorID integer primary key, firstName text, lastName text, fieldMode integer);
        create table itemCreators (itemID integer, creatorID integer, orderIndex integer);
        create table itemAttachments (
          itemID integer primary key,
          parentItemID integer,
          linkMode integer,
          contentType text,
          charsetID integer,
          path text
        );

        insert into itemTypes values (3, 'attachment'), (22, 'journalArticle');
        insert into libraries values (1, 'user');
        insert into fields values
          (1, 'title'),
          (6, 'date'),
          (13, 'url'),
          (38, 'publicationTitle'),
          (59, 'DOI');
        insert into items values (1, 'ITEMKEY1', 22, 1);
        insert into items values (2, 'ATTACH1', 3, 1);
        insert into itemDataValues values
          (1, 'Succinct Data Structures for Segments'),
          (2, '2025-00-00'),
          (3, 'LIPIcs'),
          (4, '10.4230/example'),
          (5, 'https://example.test/paper');
        insert into itemData values
          (1, 1, 1),
          (1, 6, 2),
          (1, 38, 3),
          (1, 59, 4),
          (1, 13, 5);
        insert into creators values (1, 'Philip', 'Bille', 0);
        insert into itemCreators values (1, 1, 0);
        insert into itemAttachments values
          (2, 1, 0, 'application/pdf', null, 'storage:Bille.pdf');
        """
    )
    connection.commit()
    connection.close()


class ZoteroTests(unittest.TestCase):
    def test_parse_local_api_item_formats_display_metadata(self):
        item = ZO.parse_local_api_item(api_item())

        self.assertEqual(item["key"], "ABC12345")
        self.assertEqual(item["title"], "Introduction to Online Convex Optimization")
        self.assertEqual(item["creators"], "Elad Hazan")
        self.assertEqual(item["publication"], "Lecture Notes")
        self.assertEqual(ZO.item_year(item), "2024")
        self.assertEqual(
            ZO.item_url(item),
            "https://doi.org/10.1000/example",
        )

    @mock.patch("chiyo_cli.builtin_tools.zo.local_api.urlopen")
    def test_load_items_from_local_api_filters_notes_and_title_matches(self, urlopen):
        note = api_item("NOTEKEY1", "Note")
        note["data"]["itemType"] = "note"
        author_only = api_item("AUTHOR1", "Unrelated Title")
        author_only["data"]["creators"] = [{"firstName": "Convex", "lastName": "Optimization"}]
        payload = json.dumps([api_item(), note, author_only]).encode("utf-8")
        urlopen.return_value = FakeResponse(payload)

        items = ZO.load_items_from_local_api(
            {"local_api_url": "http://localhost:23119/api/"},
            "convex optimization",
        )

        self.assertEqual([item["key"] for item in items], ["ABC12345"])
        requested_url = urlopen.call_args.args[0]
        self.assertIn("users/0/items", requested_url)
        self.assertIn("itemType=-attachment", requested_url)
        self.assertNotIn("q=", requested_url)

    def test_load_sqlite_items_reads_snapshot_and_resolves_storage_pdf(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "zotero.sqlite"
            create_sqlite_fixture(db_path)

            items = ZO.load_sqlite_items(
                {"zotero_data_dir": temp_dir},
                lambda message: self.fail(message),
            )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["key"], "ITEMKEY1")
        self.assertEqual(items[0]["creators"], "Philip Bille")
        self.assertEqual(items[0]["doi"], "10.4230/example")
        self.assertEqual(
            items[0]["attachment_path"],
            os.path.join(temp_dir, "storage", "ATTACH1", "Bille.pdf"),
        )

    def test_filter_items_matches_title_terms_only(self):
        items = [
            {"title": "Linear Algebra Done Right", "creators": "Sheldon Axler"},
            {"title": "Computer Systems", "creators": "Bryant O'Hallaron"},
        ]

        self.assertEqual(ZO.filter_items(items, "linear algebra"), [items[0]])
        self.assertEqual(ZO.filter_items(items, "axler"), [])

    @mock.patch("chiyo_cli.toolkit.choose_item_from")
    def test_choose_zotero_item_displays_title_creators_and_year_only(self, choose_item):
        items = [
            {
                "title": "MP-SPDZ",
                "creators": "Marcel Keller",
                "date": "2020",
                "publication": "CCS",
                "doi": "10.1/mp",
                "url": "",
                "item_type": "conferencePaper",
            }
        ]
        choose_item.return_value = items[0]

        tool = ZO.Tool()
        selected = tool.select_item(
            items,
            "",
            tool.parser().parse_args([]),
            {"fzf_prompt": "zo> "},
        )

        self.assertEqual(selected, items[0])
        display_fields = choose_item.call_args.kwargs["display_fields"]
        self.assertEqual(len(display_fields(items[0])), 3)
        self.assertEqual(choose_item.call_args.kwargs["search_display_fields"], [1])
        self.assertNotIn("filter_rows", choose_item.call_args.kwargs)
        self.assertEqual(choose_item.call_args.args[1], "zo> ")

    @mock.patch("chiyo_cli.builtin_tools.zo.tool.open_location")
    def test_run_prints_key_without_opening(self, open_location):
        config = {
            "local_api_url": "http://localhost:23119/api/",
            "zotero_data_dir": "/tmp/Zotero",
            "fzf_prompt": "zo> ",
        }
        tool = ZO.Tool()

        with mock.patch.object(tool, "items", return_value=[
            {
                "key": "ITEMKEY1",
                "title": "Linear Algebra Done Right",
                "creators": "Sheldon Axler",
                "date": "2015",
                "item_type": "book",
            }
        ]):
            with mock.patch("sys.stdout", new_callable=StringIO) as stdout:
                tool.run(["--print-key", "linear"], config=config)

        self.assertEqual(stdout.getvalue(), "ITEMKEY1\n")
        open_location.assert_not_called()

    @mock.patch("chiyo_cli.builtin_tools.zo.tool.open_location")
    def test_run_opens_zotero_select_uri_by_default(
        self,
        open_location,
    ):
        config = {
            "local_api_url": "http://localhost:23119/api/",
            "zotero_data_dir": "/tmp/Zotero",
            "fzf_prompt": "zo> ",
        }
        tool = ZO.Tool()

        with mock.patch.object(tool, "items", return_value=[
            {
                "key": "ITEMKEY1",
                "library_type": "user",
                "title": "Linear Algebra Done Right",
                "creators": "Sheldon Axler",
                "date": "2015",
                "item_type": "book",
            }
        ]):
            tool.run(["linear"], config=config)

        open_location.assert_called_once()
        self.assertEqual(
            open_location.call_args.args[0],
            "zotero://select/library/items/ITEMKEY1",
        )

    @mock.patch("chiyo_cli.builtin_tools.zo.attachments.urlopen")
    @mock.patch("chiyo_cli.builtin_tools.zo.local_api.urlopen")
    def test_attachment_path_uses_local_api_file_url(
        self,
        local_api_urlopen,
        attachment_urlopen,
    ):
        children = [
            {
                "key": "PDFKEY12",
                "data": {
                    "key": "PDFKEY12",
                    "itemType": "attachment",
                    "contentType": "application/pdf",
                },
            }
        ]
        local_api_urlopen.return_value = FakeResponse(json.dumps(children).encode("utf-8"))
        attachment_urlopen.return_value = FakeResponse(
            b"file:///Users/me/Zotero/storage/PDFKEY12/paper.pdf"
        )
        item = {"key": "ITEMKEY1", "source": "local-api"}

        path = ZO.attachment_path(
            {
                "local_api_url": "http://localhost:23119/api/",
                "zotero_data_dir": "~/Zotero",
            },
            item,
        )

        self.assertEqual(path, "/Users/me/Zotero/storage/PDFKEY12/paper.pdf")


if __name__ == "__main__":
    unittest.main()
