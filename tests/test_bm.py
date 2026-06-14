import os
import plistlib
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock

from chiyo_cli.builtin_tools import explorer_bookmark as BM
from chiyo_cli.tool_config import load_tool_config


def bookmark(title, url):
    return {
        "URIDictionary": {"title": title},
        "URLString": url,
    }


def folder(title, children):
    return {
        "Title": title,
        "Children": children,
    }


class BookmarkTests(unittest.TestCase):
    def test_walk_bookmarks_omits_configured_folders_from_display_path(self):
        data = folder(
            "Bookmarks",
            [
                folder(
                    "BookmarksBar",
                    [
                        bookmark("Example", "https://example.com"),
                    ],
                ),
                folder(
                    "Reading List",
                    [
                        bookmark("Later", "https://later.example"),
                    ],
                ),
            ],
        )
        config = {
            "skip_folders": {"Bookmarks", "Reading List"},
            "rename_folders": {},
        }
        results = []

        BM.walk_bookmarks(data, [], results, config)

        self.assertEqual(
            results,
            [
                ("BookmarksBar/Example", "https://example.com"),
                ("Later", "https://later.example"),
            ],
        )

    def test_walk_bookmarks_applies_optional_folder_renames(self):
        data = folder(
            "Bookmarks",
            [
                folder(
                    "BookmarksBar",
                    [
                        bookmark("Example", "https://example.com"),
                    ],
                ),
            ],
        )
        config = {
            "skip_folders": {"Bookmarks"},
            "rename_folders": {"BookmarksBar": "Personal"},
        }
        results = []

        BM.walk_bookmarks(data, [], results, config)

        self.assertEqual(results, [("Personal/Example", "https://example.com")])

    def test_load_bookmarks_reads_plist_and_removes_exact_duplicates(self):
        data = folder(
            "Bookmarks",
            [
                bookmark("Example", "https://example.com"),
                bookmark("Example", "https://example.com"),
                bookmark("Example", "https://other.example"),
            ],
        )

        with tempfile.NamedTemporaryFile(delete=False) as file:
            plistlib.dump(data, file)
            path = file.name

        try:
            config = {
                "bookmarks_path": path,
                "skip_folders": {"Bookmarks"},
                "rename_folders": {},
            }

            self.assertEqual(
                BM.load_bookmarks(BM.Tool().normalize_config(config), lambda message: self.fail(message)),
                [
                    ("Example", "https://example.com"),
                    ("Example", "https://other.example"),
                ],
            )
        finally:
            os.unlink(path)

    def test_load_config_reads_tools_toml(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tools.toml"
            path.write_text(
                "\n".join(
                    [
                        '["jingke-zhang/explorer-bookmark"]',
                        'bookmarks_path = "~/Bookmarks.plist"',
                        'skip_folders = ["Bookmarks"]',
                        'fzf_prompt = "bookmarks> "',
                        'browser = "Google Chrome"',
                    ]
                ),
                encoding="utf-8",
            )

            config = load_tool_config("jingke-zhang/explorer-bookmark", BM.DEFAULT_CONFIG, config_path=str(path))
            config = BM.Tool().normalize_config(config)

        self.assertTrue(str(config["bookmarks_path"]).endswith("Bookmarks.plist"))
        self.assertEqual(config["browser"], "Google Chrome")

    @mock.patch("chiyo_cli.fzf.choose_item")
    def test_choose_bookmark_preserves_duplicate_display_names(self, choose_item):
        bookmarks = [
            ("Example", "https://first.example"),
            ("Example", "https://second.example"),
        ]
        choose_item.return_value = bookmarks[1]

        selected = BM.Tool().select_item(
            bookmarks,
            "",
            BM.Tool().parser().parse_args([]),
            {"fzf_prompt": "bm> "},
        )

        self.assertEqual(selected, ("Example", "https://second.example"))
        self.assertEqual(choose_item.call_args.args[0], bookmarks)
        self.assertEqual(choose_item.call_args.kwargs["search_display_fields"], [1])
        self.assertNotIn("filter_rows", choose_item.call_args.kwargs)

    def test_filter_bookmarks_matches_display_name_only(self):
        bookmarks = [
            ("Personal/Example", "https://docs.example.com"),
            ("Work/Other", "https://example.com"),
        ]

        tool = BM.Tool()
        self.assertEqual(
            [item for item in bookmarks if tool.match(item, "Personal", {})],
            [("Personal/Example", "https://docs.example.com")],
        )
        self.assertEqual([item for item in bookmarks if tool.match(item, "docs.example", {})], [])

    def test_list_completions_prints_bookmark_paths(self):
        bookmarks = [
            ("Academic/Google Scholar", "https://scholar.google.com"),
            ("Personal/YouTube", "https://youtube.com"),
        ]

        with mock.patch("sys.stdout", new_callable=StringIO) as stdout:
            tool = BM.Tool()
            with mock.patch.object(tool, "items", return_value=bookmarks):
                tool.print_completions({})

        self.assertEqual(stdout.getvalue(), "Academic/Google Scholar\nPersonal/YouTube\n")

    @mock.patch("chiyo_cli.toolkit.open_with_app")
    def test_run_lists_completions_without_opening_url(self, open_with_app):
        config = {
            "bookmarks_path": "/tmp/bookmarks.plist",
            "skip_folders": set(),
            "rename_folders": {},
            "fzf_prompt": "bm> ",
            "browser": "Safari",
        }
        tool = BM.Tool()

        with mock.patch.object(tool, "items", return_value=[
            ("Academic/Google Scholar", "https://scholar.google.com"),
        ]):
            with mock.patch("sys.stdout", new_callable=StringIO) as stdout:
                tool.run(["--list-completions"], config=config)

        self.assertEqual(stdout.getvalue(), "Academic/Google Scholar\n")
        open_with_app.assert_not_called()

    @mock.patch("chiyo_cli.fzf.choose_item")
    def test_select_bookmark_returns_single_match_directly_when_allowed(self, choose):
        selected = BM.Tool().select_item(
            [("Example", "https://example.com")],
            "Example",
            BM.Tool().parser().parse_args(["Example"]),
            {"fzf_prompt": "bm> "},
        )

        self.assertEqual(selected, ("Example", "https://example.com"))
        choose.assert_not_called()

    @mock.patch("chiyo_cli.fzf.choose_item", return_value=("Example", "https://example.com"))
    def test_select_bookmark_uses_fzf_for_single_match_without_query(self, choose):
        selected = BM.Tool().select_item(
            [("Example", "https://example.com")],
            "",
            BM.Tool().parser().parse_args([]),
            {"fzf_prompt": "bm> "},
        )

        self.assertEqual(selected, ("Example", "https://example.com"))
        choose.assert_called_once()


if __name__ == "__main__":
    unittest.main()
