import os
import plistlib
import tempfile
import unittest
from io import StringIO
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
BM = SourceFileLoader("bm", str(REPO_ROOT / "bin" / "bm")).load_module()


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
                BM.load_bookmarks(config),
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
                        "[bm]",
                        'bookmarks_path = "~/Bookmarks.plist"',
                        'skip_folders = ["Bookmarks"]',
                        'fzf_prompt = "bookmarks> "',
                        'browser = "Google Chrome"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(BM, "TOOLS_CONFIG_PATH", str(path)):
                config = BM.load_config()

        self.assertTrue(config["bookmarks_path"].endswith("Bookmarks.plist"))
        self.assertEqual(config["browser"], "Google Chrome")

    @mock.patch("bm.choose_item")
    def test_choose_bookmark_preserves_duplicate_display_names(self, choose_item):
        bookmarks = [
            ("Example", "https://first.example"),
            ("Example", "https://second.example"),
        ]
        choose_item.return_value = bookmarks[1]

        selected = BM.choose_bookmark(bookmarks, {"fzf_prompt": "bm> "})

        self.assertEqual(selected, "https://second.example")
        self.assertEqual(choose_item.call_args.args[0], bookmarks)
        self.assertEqual(choose_item.call_args.kwargs["search_display_fields"], [1])
        self.assertNotIn("filter_rows", choose_item.call_args.kwargs)

    def test_filter_bookmarks_matches_display_name_only(self):
        bookmarks = [
            ("Personal/Example", "https://docs.example.com"),
            ("Work/Other", "https://example.com"),
        ]

        self.assertEqual(
            BM.filter_bookmarks(bookmarks, "Personal"),
            [("Personal/Example", "https://docs.example.com")],
        )
        self.assertEqual(BM.filter_bookmarks(bookmarks, "docs.example"), [])

    def test_list_completions_prints_bookmark_paths(self):
        bookmarks = [
            ("Academic/Google Scholar", "https://scholar.google.com"),
            ("Personal/YouTube", "https://youtube.com"),
        ]

        with mock.patch("sys.stdout", new_callable=StringIO) as stdout:
            BM.list_completions(bookmarks)

        self.assertEqual(stdout.getvalue(), "Academic/Google Scholar\nPersonal/YouTube\n")

    @mock.patch("bm.open_url")
    @mock.patch("bm.load_bookmarks")
    @mock.patch("bm.load_config")
    def test_main_lists_completions_without_opening_url(
        self,
        load_config,
        load_bookmarks,
        open_url,
    ):
        load_config.return_value = {
            "bookmarks_path": "/tmp/bookmarks.plist",
            "skip_folders": set(),
            "rename_folders": {},
            "fzf_prompt": "bm> ",
            "browser": "Safari",
        }
        load_bookmarks.return_value = [
            ("Academic/Google Scholar", "https://scholar.google.com"),
        ]

        with mock.patch("sys.stdout", new_callable=StringIO) as stdout:
            BM.main(["--list-completions"])

        self.assertEqual(stdout.getvalue(), "Academic/Google Scholar\n")
        open_url.assert_not_called()

    @mock.patch("bm.choose_bookmark")
    def test_select_bookmark_returns_single_match_directly_when_allowed(self, choose):
        selected = BM.select_bookmark(
            [("Example", "https://example.com")],
            {"fzf_prompt": "bm> "},
            allow_direct=True,
        )

        self.assertEqual(selected, "https://example.com")
        choose.assert_not_called()

    @mock.patch("bm.choose_bookmark", return_value="https://example.com")
    def test_select_bookmark_uses_fzf_for_single_match_without_query(self, choose):
        selected = BM.select_bookmark(
            [("Example", "https://example.com")],
            {"fzf_prompt": "bm> "},
            allow_direct=False,
        )

        self.assertEqual(selected, "https://example.com")
        choose.assert_called_once()


if __name__ == "__main__":
    unittest.main()
