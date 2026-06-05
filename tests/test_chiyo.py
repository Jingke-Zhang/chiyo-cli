import os
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
CHIYO = SourceFileLoader("chiyo", str(REPO_ROOT / "bin" / "chiyo")).load_module()


class ChiyoTests(unittest.TestCase):
    def test_init_zsh_prints_path_and_gop_source(self):
        script = CHIYO.init_zsh()

        self.assertNotIn("export PATH=", script)
        self.assertIn(
            f'fpath=("{os.path.expanduser(CHIYO.ZSH_SITE_FUNCTIONS_DIR)}" $fpath)',
            script,
        )
        self.assertIn("autoload -Uz compinit", script)
        self.assertIn("compinit", script)
        self.assertIn(
            f'source "{os.path.join(CHIYO.SHELL_DIR, "gop.zsh")}"',
            script,
        )

    @mock.patch("chiyo.shutil.which")
    def test_doctor_lines_reports_missing_development_install(self, which):
        which.return_value = None

        with tempfile.TemporaryDirectory() as temp_dir:
            local_bin = os.path.join(temp_dir, ".local", "bin")
            site_functions = os.path.join(
                temp_dir,
                ".local",
                "share",
                "zsh",
                "site-functions",
            )
            config_path = os.path.join(temp_dir, "config.toml")

            with mock.patch.object(CHIYO, "LOCAL_BIN_DIR", local_bin):
                with mock.patch.object(CHIYO, "ZSH_SITE_FUNCTIONS_DIR", site_functions):
                    with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                        with mock.patch.dict(os.environ, {"HOME": temp_dir, "PATH": ""}):
                            lines = CHIYO.doctor_lines()

        self.assertIn("missing fzf: not found", lines)
        self.assertIn(f"missing bm symlink: {local_bin}/bm not found", lines)
        self.assertIn(f"todo    PATH: add {local_bin} to PATH", lines)
        self.assertIn("Run: ./install.sh", lines)
        self.assertIn("Review todo items above.", lines)

    @mock.patch("chiyo.shutil.which")
    def test_doctor_lines_reports_valid_development_install(self, which):
        which.side_effect = lambda name: f"/usr/bin/{name}"

        with tempfile.TemporaryDirectory() as temp_dir:
            local_bin = os.path.join(temp_dir, ".local", "bin")
            site_functions = os.path.join(
                temp_dir,
                ".local",
                "share",
                "zsh",
                "site-functions",
            )
            config_path = os.path.join(temp_dir, "config.toml")
            zshrc_path = os.path.join(temp_dir, ".zshrc")
            os.makedirs(local_bin)
            os.makedirs(site_functions)
            Path(config_path).write_text("", encoding="utf-8")
            Path(zshrc_path).write_text(CHIYO.SHELL_INTEGRATION, encoding="utf-8")

            for command in CHIYO.COMMANDS:
                os.symlink(
                    os.path.join(CHIYO.BIN_DIR, command),
                    os.path.join(local_bin, command),
                )

            for completion in CHIYO.COMPLETIONS:
                os.symlink(
                    os.path.join(CHIYO.COMPLETIONS_DIR, completion),
                    os.path.join(site_functions, completion),
                )

            with mock.patch.object(CHIYO, "LOCAL_BIN_DIR", local_bin):
                with mock.patch.object(CHIYO, "ZSH_SITE_FUNCTIONS_DIR", site_functions):
                    with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                        with mock.patch.dict(
                            os.environ,
                            {
                                "HOME": temp_dir,
                                "PATH": os.pathsep.join([local_bin, "/usr/bin"]),
                            },
                        ):
                            lines = CHIYO.doctor_lines()

        self.assertIn(
            f"ok      bm symlink: {local_bin}/bm -> {CHIYO.BIN_DIR}/bm",
            lines,
        )
        self.assertIn(
            f"ok      _bm completion: {site_functions}/_bm -> {CHIYO.COMPLETIONS_DIR}/_bm",
            lines,
        )
        self.assertIn(
            f"ok      zsh integration: {zshrc_path} contains {CHIYO.SHELL_INTEGRATION}",
            lines,
        )
        self.assertNotIn("Run: ./install.sh", lines)

    def test_check_symlink_warns_when_link_points_elsewhere(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = os.path.join(temp_dir, "bm")
            os.symlink("/old/repo/bin/bm", target)

            self.assertEqual(
                CHIYO.check_symlink("bm symlink", target, "/new/repo/bin/bm"),
                (
                    "warn",
                    f"{target} -> /old/repo/bin/bm; expected /new/repo/bin/bm",
                    "bm symlink",
                ),
            )

    @mock.patch("chiyo.shutil.which")
    def test_doctor_lines_reports_available_command(self, which):
        which.side_effect = lambda name: f"/usr/bin/{name}"

        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.object(CHIYO, "LOCAL_BIN_DIR", os.path.join(temp_dir, "bin")):
                with mock.patch.object(
                    CHIYO,
                    "ZSH_SITE_FUNCTIONS_DIR",
                    os.path.join(temp_dir, "site-functions"),
                ):
                    with mock.patch.dict(os.environ, {"HOME": temp_dir}):
                        lines = CHIYO.doctor_lines()

        self.assertIn("ok      fzf: /usr/bin/fzf", lines)


if __name__ == "__main__":
    unittest.main()
