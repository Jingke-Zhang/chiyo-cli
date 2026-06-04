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
            "         \033[3;4mhttps://example.com\033[0m\t#3",
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
            "  \033[3;4mhttps://example.com\033[0m\t#1",
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


if __name__ == "__main__":
    unittest.main()
