import os
import plistlib
import subprocess
import tempfile
import unittest
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

    @mock.patch("bm.shutil.which", return_value="/usr/bin/fzf")
    @mock.patch("bm.subprocess.run")
    def test_choose_bookmark_preserves_duplicate_display_names(self, run, _which):
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="Example\thttps://second.example\t#1\n",
            stderr="",
        )
        bookmarks = [
            ("Example", "https://first.example"),
            ("Example", "https://second.example"),
        ]

        selected = BM.choose_bookmark(bookmarks, {"fzf_prompt": "bm> "})

        self.assertEqual(selected, "https://second.example")


if __name__ == "__main__":
    unittest.main()
