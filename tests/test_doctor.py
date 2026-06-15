import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from chiyo_cli.commands import doctor as DOCTOR
from chiyo_cli.commands import install as INSTALL


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_TOOL_DIR = REPO_ROOT / "tests" / "fixtures" / "user_tools"


class DoctorTests(unittest.TestCase):
    def test_init_zsh_prints_loader_for_installed_shell_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            completion_dir = os.path.join(temp_dir, "zsh")
            shell_dir = os.path.join(temp_dir, "shell")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        "tool_dirs = []",
                        "enabled_tools = []",
                        'wrapper_dir = "~/.local/bin"',
                        f'completion_dir = "{completion_dir}"',
                        f'shell_dir = "{shell_dir}"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(DOCTOR, "CONFIG_PATH", config_path):
                script = DOCTOR.init_zsh()

        self.assertIn(
            "# Config: run `chiyo config init --all --append` once for explicit defaults.",
            script,
        )
        self.assertNotIn("export PATH=", script)
        self.assertIn(
            f'fpath=("{completion_dir}" $fpath)',
            script,
        )
        self.assertIn("autoload -Uz compinit", script)
        self.assertIn("compinit", script)
        self.assertIn(f'for chiyo_shell_file in "{shell_dir}"/*.zsh; do', script)
        self.assertIn('source "$chiyo_shell_file"', script)

    @mock.patch("chiyo_cli.commands.doctor.shutil.which")
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

            with mock.patch.object(DOCTOR, "LOCAL_BIN_DIR", local_bin):
                with mock.patch.object(DOCTOR, "ZSH_SITE_FUNCTIONS_DIR", site_functions):
                    with mock.patch.object(DOCTOR, "CONFIG_PATH", config_path):
                        with mock.patch.dict(os.environ, {"HOME": temp_dir, "PATH": ""}):
                            lines = DOCTOR.doctor_lines()

        self.assertIn("missing fzf: not found", lines)
        self.assertIn("missing rg: not found", lines)
        self.assertIn(f"missing chiyo symlink: {local_bin}/chiyo not found", lines)
        self.assertIn(f"todo    PATH: add {local_bin} to PATH", lines)
        self.assertIn("Run: ./install.sh", lines)
        self.assertIn("Review todo items above.", lines)

    @mock.patch("chiyo_cli.commands.doctor.shutil.which")
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
            Path(zshrc_path).write_text(DOCTOR.SHELL_INTEGRATION, encoding="utf-8")

            for command in DOCTOR.COMMANDS:
                os.symlink(
                    os.path.join(INSTALL.BIN_DIR, command),
                    os.path.join(local_bin, command),
                )

            with mock.patch.object(DOCTOR, "LOCAL_BIN_DIR", local_bin):
                with mock.patch.object(DOCTOR, "ZSH_SITE_FUNCTIONS_DIR", site_functions):
                    with mock.patch.object(DOCTOR, "CONFIG_PATH", config_path):
                        with mock.patch.dict(
                            os.environ,
                            {
                                "HOME": temp_dir,
                                "PATH": os.pathsep.join([local_bin, "/usr/bin"]),
                            },
                        ):
                            lines = DOCTOR.doctor_lines()

        self.assertIn(f"ok      chiyo symlink: {local_bin}/chiyo -> {INSTALL.BIN_DIR}/chiyo", lines)
        self.assertIn(
            f"ok      zsh integration: {zshrc_path} contains {DOCTOR.SHELL_INTEGRATION}",
            lines,
        )
        self.assertNotIn("Run: ./install.sh", lines)

    def test_check_symlink_warns_when_link_points_elsewhere(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = os.path.join(temp_dir, "bm")
            os.symlink("/old/repo/bin/bm", target)

            self.assertEqual(
                DOCTOR.check_symlink("bm symlink", target, "/new/repo/bin/bm"),
                (
                    "warn",
                    f"{target} -> /old/repo/bin/bm; expected /new/repo/bin/bm",
                    "bm symlink",
                ),
            )

    @mock.patch("chiyo_cli.commands.doctor.shutil.which")
    def test_doctor_lines_reports_available_command(self, which):
        which.side_effect = lambda name: f"/usr/bin/{name}"

        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.object(DOCTOR, "LOCAL_BIN_DIR", os.path.join(temp_dir, "bin")):
                with mock.patch.object(
                    DOCTOR,
                    "ZSH_SITE_FUNCTIONS_DIR",
                    os.path.join(temp_dir, "site-functions"),
                ):
                    with mock.patch.dict(os.environ, {"HOME": temp_dir}):
                        lines = DOCTOR.doctor_lines()

        self.assertIn("ok      fzf: /usr/bin/fzf", lines)

    def test_user_tool_doctor_checks_report_metadata_and_install_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper_dir = Path(temp_dir) / "bin"
            wrapper_dir.mkdir()
            completion_dir = Path(temp_dir) / "zsh"
            completion_dir.mkdir()
            (wrapper_dir / "paper").write_text(
                INSTALL.wrapper_script("paper"),
                encoding="utf-8",
            )
            (completion_dir / "_paper").write_text(
                INSTALL.completion_script("paper"),
                encoding="utf-8",
            )
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = ["missing"]',
                        f'wrapper_dir = "{wrapper_dir}"',
                        f'completion_dir = "{completion_dir}"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(DOCTOR, "CONFIG_PATH", config_path):
                lines = [
                    f"{status:7} {label}: {detail}"
                    for status, detail, label in DOCTOR.user_tool_doctor_checks()
                ]

        output = "\n".join(lines)
        self.assertIn("ok      user tool fixture/paper-search metadata:", output)
        self.assertIn("warn    user tool missing: enabled but not discoverable", output)
        self.assertIn("ok      user tool fixture/paper-search wrapper:", output)
        self.assertIn("ok      user tool fixture/paper-search zsh:", output)
        self.assertIn(
            "warn    user tool fixture/paper-search: fixture/paper-search installed but disabled for chiyo run",
            output,
        )
        self.assertIn("warn    user tool missing_author.py:", output)
        self.assertIn("warn    user tool conflicting_flags.py:", output)

    def test_user_tool_doctor_checks_report_shell_tool_install_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper_dir = Path(temp_dir) / "bin"
            wrapper_dir.mkdir()
            completion_dir = Path(temp_dir) / "zsh"
            completion_dir.mkdir()
            shell_dir = Path(temp_dir) / "shell"
            shell_dir.mkdir()
            (wrapper_dir / "gtd").write_text(
                INSTALL.wrapper_script("gtd"),
                encoding="utf-8",
            )
            (shell_dir / "gtd.zsh").write_text(
                INSTALL.shell_function_script("gtd"),
                encoding="utf-8",
            )
            (completion_dir / "_gtd").write_text(
                INSTALL.completion_script("gtd"),
                encoding="utf-8",
            )
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        "tool_dirs = []",
                        'enabled_tools = ["jingke-zhang/gtd"]',
                        f'wrapper_dir = "{wrapper_dir}"',
                        f'completion_dir = "{completion_dir}"',
                        f'shell_dir = "{shell_dir}"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(DOCTOR, "CONFIG_PATH", config_path):
                lines = [
                    f"{status:7} {label}: {detail}"
                    for status, detail, label in DOCTOR.user_tool_doctor_checks()
                ]

        output = "\n".join(lines)
        self.assertIn("ok      user tool jingke-zhang/gtd shell:", output)
        self.assertIn("ok      user tool jingke-zhang/gtd zsh:", output)
        self.assertIn(
            "warn    user tool jingke-zhang/gtd wrapper:",
            output,
        )
        self.assertIn("old generated wrapper", output)

    def test_user_tool_doctor_checks_warn_when_installed_completion_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper_dir = Path(temp_dir) / "bin"
            wrapper_dir.mkdir()
            completion_dir = Path(temp_dir) / "zsh"
            (wrapper_dir / "paper").write_text(
                INSTALL.wrapper_script("paper"),
                encoding="utf-8",
            )
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = ["fixture/paper-search"]',
                        f'wrapper_dir = "{wrapper_dir}"',
                        f'completion_dir = "{completion_dir}"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(DOCTOR, "CONFIG_PATH", config_path):
                lines = [
                    f"{status:7} {label}: {detail}"
                    for status, detail, label in DOCTOR.user_tool_doctor_checks()
                ]

        self.assertIn(
            f"warn    user tool fixture/paper-search zsh: {completion_dir / '_paper'} not found",
            "\n".join(lines),
        )


if __name__ == "__main__":
    unittest.main()
