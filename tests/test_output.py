import unittest
from io import StringIO
from unittest import mock

from chiyo_cli.output import print_warning


class FakeTTY(StringIO):
    def isatty(self):
        return True


class OutputTests(unittest.TestCase):
    def test_print_warning_colors_label_on_tty(self):
        stderr = FakeTTY()

        with mock.patch("sys.stderr", stderr):
            with mock.patch.dict("os.environ", {}, clear=True):
                print_warning("tool", "careful")

        self.assertEqual(stderr.getvalue(), "tool: \033[33mwarning\033[0m: careful\n")

    def test_print_warning_omits_color_when_no_color_is_set(self):
        stderr = FakeTTY()

        with mock.patch("sys.stderr", stderr):
            with mock.patch.dict("os.environ", {"NO_COLOR": "1"}):
                print_warning("tool", "careful")

        self.assertEqual(stderr.getvalue(), "tool: warning: careful\n")


if __name__ == "__main__":
    unittest.main()
