import subprocess
import unittest
from unittest import mock

from chiyo_cli.fzf import (
    Field,
    STYLE_PRIMARY,
    STYLE_SECONDARY,
    choose_item,
    display_width,
    format_row,
    format_rows,
)


class FzfTests(unittest.TestCase):
    def test_format_row_styles_and_aligns_fields(self):
        row = format_row(
            3,
            [
                Field("Personal/Example", STYLE_PRIMARY),
                Field("https://example.com", STYLE_SECONDARY),
            ],
            [len("Personal/Longer Example"), len("https://example.com")],
        )

        self.assertEqual(
            row,
            "\033[1;32mPersonal/Example\033[0m"
            "         \t\033[3;4mhttps://example.com\033[0m\t#3",
        )

    def test_format_row_aligns_wide_characters_by_display_width(self):
        row = format_row(
            1,
            [
                Field("BookmarksBar/ペン字", STYLE_PRIMARY),
                Field("https://example.com", STYLE_SECONDARY),
            ],
            [display_width("BookmarksBar/Longer"), len("https://example.com")],
        )

        self.assertEqual(
            row,
            "\033[1;32mBookmarksBar/ペン字\033[0m"
            "  \t\033[3;4mhttps://example.com\033[0m\t#1",
        )

    @mock.patch("chiyo_cli.fzf.shutil.which", return_value="/usr/bin/fzf")
    @mock.patch("chiyo_cli.fzf.subprocess.run")
    def test_choose_item_returns_item_by_hidden_index(self, run, _which):
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="Example\t#1\n",
            stderr="",
        )
        items = ["first", "second"]

        selected = choose_item(
            items,
            [[Field("First")], [Field("Second")]],
            "x> ",
            "an item",
            lambda message: self.fail(message),
        )

        self.assertEqual(selected, "second")
        self.assertIn("--ansi", run.call_args.args[0])
        self.assertIn("--with-nth=1", run.call_args.args[0])
        self.assertIn("--nth=1", run.call_args.args[0])

    def test_format_rows_separates_visible_fields_from_index(self):
        rows = format_rows(
            [[Field("Safari"), Field("/Applications/Safari.app")]],
        )

        self.assertEqual(
            rows,
            ["Safari  \t/Applications/Safari.app\t#0"],
        )

    def test_format_rows_can_add_hidden_filter_fields(self):
        rows = format_rows(
            [[Field("Safari"), Field("/Applications/Safari.app")]],
            [["Safari", "browser"]],
        )

        self.assertEqual(
            rows,
            [
                "Safari  \t/Applications/Safari.app"
                "\t\033[8mSafari\033[0m\t\033[8mbrowser\033[0m\t#0"
            ],
        )

    @mock.patch("chiyo_cli.fzf.shutil.which", return_value="/usr/bin/fzf")
    @mock.patch("chiyo_cli.fzf.subprocess.run")
    def test_choose_item_can_limit_search_to_selected_fields(self, run, _which):
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="Safari\t/Applications/Safari.app\t#0\n",
            stderr="",
        )

        selected = choose_item(
            ["Safari"],
            [[Field("Safari"), Field("/Applications/Safari.app")]],
            "x> ",
            "an item",
            lambda message: self.fail(message),
            search_field_numbers=[1],
        )

        self.assertEqual(selected, "Safari")
        self.assertIn("--with-nth=1,2", run.call_args.args[0])
        self.assertIn("--nth=1", run.call_args.args[0])
        self.assertIn("/Applications/Safari.app\t#0", run.call_args.kwargs["input"])

    @mock.patch("chiyo_cli.fzf.shutil.which", return_value="/usr/bin/fzf")
    @mock.patch("chiyo_cli.fzf.subprocess.run")
    def test_choose_item_can_search_hidden_filter_rows(self, run, _which):
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="Safari\t/Applications/Safari.app\tSafari\tbrowser\t#0\n",
            stderr="",
        )

        selected = choose_item(
            ["Safari"],
            [[Field("Safari"), Field("/Applications/Safari.app")]],
            "x> ",
            "an item",
            lambda message: self.fail(message),
            filter_rows=[["Safari", "browser"]],
        )

        self.assertEqual(selected, "Safari")
        self.assertIn("--with-nth=1,2,3,4", run.call_args.args[0])
        self.assertIn("--nth=3,4", run.call_args.args[0])
        self.assertIn(
            "/Applications/Safari.app"
            "\t\033[8mSafari\033[0m\t\033[8mbrowser\033[0m\t#0",
            run.call_args.kwargs["input"],
        )

    def test_choose_item_rejects_two_filter_interfaces(self):
        with self.assertRaises(ValueError):
            choose_item(
                ["Safari"],
                [[Field("Safari")]],
                "x> ",
                "an item",
                lambda message: self.fail(message),
                search_field_numbers=[1],
                filter_rows=[["Safari"]],
            )


if __name__ == "__main__":
    unittest.main()
