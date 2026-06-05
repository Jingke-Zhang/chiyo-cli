import os
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
CHIYO = SourceFileLoader("chiyo", str(REPO_ROOT / "bin" / "chiyo")).load_module()


class ChiyoTests(unittest.TestCase):
    def test_init_zsh_prints_path_and_gop_source(self):
        script = CHIYO.init_zsh()

        self.assertIn(f'export PATH="{CHIYO.BIN_DIR}:$PATH"', script)
        self.assertIn(
            f'source "{os.path.join(CHIYO.SHELL_DIR, "gop.zsh")}"',
            script,
        )

    @mock.patch("chiyo.shutil.which")
    @mock.patch("chiyo.os.path.exists")
    def test_doctor_lines_reports_missing_setup(self, exists, which):
        which.return_value = None
        exists.return_value = False

        lines = CHIYO.doctor_lines()

        self.assertIn("missing fzf: not found", lines)
        self.assertIn("Run: chiyo init zsh >> ~/.zshrc", lines)

    @mock.patch("chiyo.shutil.which", return_value=None)
    @mock.patch("chiyo.os.path.exists")
    def test_doctor_lines_reports_bundled_tool_not_in_path(self, exists, _which):
        exists.side_effect = lambda path: path == os.path.join(
            CHIYO.BIN_DIR,
            "gop-select",
        )

        lines = CHIYO.doctor_lines()

        self.assertIn(
            f"missing gop-select: not in PATH; bundled at {CHIYO.BIN_DIR}/gop-select",
            lines,
        )

    @mock.patch("chiyo.shutil.which")
    @mock.patch("chiyo.os.path.exists", return_value=True)
    def test_doctor_lines_reports_available_command(self, _exists, which):
        which.side_effect = lambda name: f"/usr/bin/{name}"

        lines = CHIYO.doctor_lines()

        self.assertIn("ok      fzf: /usr/bin/fzf", lines)


if __name__ == "__main__":
    unittest.main()
