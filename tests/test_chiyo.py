import os
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock

from chiyo_cli import cli as CHIYO
from chiyo_cli.toolkit import ShellAction


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_TOOL_DIR = REPO_ROOT / "tests" / "fixtures" / "user_tools"


class ChiyoTests(unittest.TestCase):
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

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                script = CHIYO.init_zsh()

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

    @mock.patch("chiyo_cli.cli.shutil.which")
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
        self.assertIn("missing rg: not found", lines)
        self.assertIn(f"missing chiyo symlink: {local_bin}/chiyo not found", lines)
        self.assertIn(f"todo    PATH: add {local_bin} to PATH", lines)
        self.assertIn("Run: ./install.sh", lines)
        self.assertIn("Review todo items above.", lines)

    @mock.patch("chiyo_cli.cli.shutil.which")
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

        self.assertIn(f"ok      chiyo symlink: {local_bin}/chiyo -> {CHIYO.BIN_DIR}/chiyo", lines)
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

    @mock.patch("chiyo_cli.cli.shutil.which")
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

    def test_tool_enable_and_disable_update_chiyo_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = ["jingke-zhang/go-or-pick", "jingke-zhang/web-search", "jingke-zhang/workspace"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                self.assertEqual(CHIYO.enable_tool_lines("paper"), ["enabled tool: fixture/paper-search"])
                self.assertEqual(CHIYO.disable_tool_lines("paper"), ["disabled tool: fixture/paper-search"])
                self.assertEqual(
                    CHIYO.disable_tool_lines("paper"),
                    ["tool already disabled: fixture/paper-search"],
                )

            content = Path(config_path).read_text(encoding="utf-8")

        self.assertIn("[chiyo]", content)
        self.assertIn('enabled_tools = ["jingke-zhang/go-or-pick", "jingke-zhang/web-search", "jingke-zhang/workspace"]', content)

    def test_tool_list_shows_discovered_tools_and_enabled_status(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = ["fixture/paper-search"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                lines = CHIYO.tool_list_lines()

        output = "\n".join(lines)
        self.assertIn("enabled  Paper Search", output)
        self.assertIn("paper", output)
        self.assertIn("Fixture Author", output)
        self.assertIn("Search fixture papers and open PDFs.", output)
        self.assertIn("disabled Disabled Notes", output)
        self.assertIn("disabled-notes", output)
        self.assertIn("warn", output)
        self.assertIn("missing_author.py", output)
        self.assertNotIn("# Paper Search", output)

    def test_tool_list_can_include_docs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = []',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                lines = CHIYO.tool_list_lines(include_docs=True)

        self.assertIn("# Paper Search", "\n".join(lines))

    def test_tool_list_reports_invalid_configured_cmds(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_config_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = ["fixture/paper-search"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )
            Path(tools_config_path).write_text(
                "\n".join(
                    [
                        '["fixture/paper-search"]',
                        'cmds = ["paper", "Bad Cmd"]',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_config_path):
                    lines = CHIYO.tool_list_lines()

        self.assertIn(
            "error    invalid cmd Bad Cmd: fixture/paper-search: cmd must match",
            "\n".join(lines),
        )

    def test_tool_doc_lines_returns_docs_for_discoverable_tool(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = []',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                lines = CHIYO.tool_doc_lines("paper")

        self.assertIn("# Paper Search", "\n".join(lines))

    def test_tool_doc_lines_returns_none_for_unknown_tool(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = []',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                lines = CHIYO.tool_doc_lines("missing")

        self.assertIsNone(lines)

    def test_main_doc_prints_docs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = []',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch("sys.stdout", new_callable=StringIO) as stdout:
                    CHIYO.main(["doc", "paper"])

        self.assertIn("# Paper Search", stdout.getvalue())

    def test_run_tool_runs_enabled_tool_with_tools_toml_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "papers"
            root.mkdir()
            alpha = root / "alpha.pdf"
            beta = root / "beta.pdf"
            alpha.write_text("alpha", encoding="utf-8")
            beta.write_text("beta", encoding="utf-8")
            config_path = os.path.join(temp_dir, "config.toml")
            tools_config_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = ["fixture/paper-search"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )
            Path(tools_config_path).write_text(
                "\n".join(
                    [
                        '["fixture/paper-search"]',
                        f'root = "{root}"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_config_path):
                    result = CHIYO.run_tool("paper", ["alpha"])

        self.assertEqual(result, str(alpha))

    def test_run_tool_uses_configured_cmd_alias(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "papers"
            root.mkdir()
            alpha = root / "alpha.pdf"
            alpha.write_text("alpha", encoding="utf-8")
            config_path = os.path.join(temp_dir, "config.toml")
            tools_config_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = ["fixture/paper-search"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )
            Path(tools_config_path).write_text(
                "\n".join(
                    [
                        '["fixture/paper-search"]',
                        f'root = "{root}"',
                        'cmds = ["paper", "papers"]',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_config_path):
                    result = CHIYO.run_tool("papers", ["alpha"])

        self.assertEqual(result, str(alpha))

    def test_run_tool_rejects_duplicate_configured_cmd(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_config_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = ["fixture/paper-search", "fixture/disabled-notes"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )
            Path(tools_config_path).write_text(
                "\n".join(
                    [
                        '["fixture/paper-search"]',
                        'cmds = ["paper"]',
                        "",
                        '["fixture/disabled-notes"]',
                        'cmds = ["paper"]',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_config_path):
                    with self.assertRaisesRegex(CHIYO.ToolCommandError, "duplicate cmd paper"):
                        CHIYO.run_tool("paper", [])

                    with self.assertRaisesRegex(CHIYO.ToolCommandError, "duplicate cmd paper"):
                        CHIYO.run_tool("fixture/paper-search", [])

    def test_run_tool_rejects_invalid_configured_cmd(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_config_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = ["fixture/paper-search"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )
            Path(tools_config_path).write_text(
                "\n".join(
                    [
                        '["fixture/paper-search"]',
                        'cmds = ["paper", "Bad Cmd"]',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_config_path):
                    with self.assertRaisesRegex(CHIYO.ToolCommandError, "invalid cmd"):
                        CHIYO.run_tool("paper", [])

    def test_run_tool_rejects_disabled_tool(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = []',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with self.assertRaises(CHIYO.ToolCommandError):
                    CHIYO.run_tool("paper", [])

    def test_run_tool_rejects_unknown_enabled_tool(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = ["missing"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with self.assertRaises(CHIYO.ToolCommandError):
                    CHIYO.run_tool("missing", [])

    def test_shell_tool_lines_render_shell_action(self):
        with mock.patch.object(CHIYO, "run_tool") as run_tool:
            run_tool.return_value = ShellAction.cd("/tmp/My Project")

            lines = CHIYO.shell_tool_lines("proj", ["my"])

        self.assertEqual(lines, ["cd '/tmp/My Project'"])
        run_tool.assert_called_once_with(
            "proj",
            ["my"],
            execute_shell_actions=False,
        )

    def test_shell_tool_lines_prints_plain_result_safely(self):
        with mock.patch.object(CHIYO, "run_tool") as run_tool:
            run_tool.return_value = "plain value"

            lines = CHIYO.shell_tool_lines("tool", [])

        self.assertEqual(lines, ["printf '%s\\n' 'plain value'"])

    def test_run_tool_runs_builtin_s(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_config_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        'tool_dirs = []',
                        'enabled_tools = ["jingke-zhang/web-search"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_config_path):
                    with mock.patch("chiyo_cli.toolkit.open_location") as open_location:
                        result = CHIYO.run_tool("s", ["g", "wavelet", "tree"])

        self.assertEqual(result, "https://www.google.com/search?q=wavelet%20tree")
        open_location.assert_called_once_with(
            "https://www.google.com/search?q=wavelet%20tree"
        )

    def test_run_tool_runs_builtin_app_alias(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_config_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        'tool_dirs = []',
                        'enabled_tools = ["jingke-zhang/application"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )
            Path(tools_config_path).write_text(
                "\n".join(
                    [
                        '["jingke-zhang/application".alias]',
                        'browser = "Safari"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_config_path):
                    with mock.patch("chiyo_cli.builtin_tools.application.open_app") as open_app:
                        result = CHIYO.run_tool("app", ["browser"])

        self.assertEqual(result, {"name": "Safari", "path": None})
        open_app.assert_called_once()
        self.assertEqual(open_app.call_args.args[0], {"name": "Safari", "path": None})

    def test_run_tool_runs_builtin_bm_print_url(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_config_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        'tool_dirs = []',
                        'enabled_tools = ["jingke-zhang/explorer-bookmark"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_config_path):
                    with mock.patch("chiyo_cli.builtin_tools.explorer_bookmark.load_bookmarks") as load_bookmarks:
                        load_bookmarks.return_value = [
                            ("Docs/Example", "https://example.test"),
                        ]
                        with mock.patch("sys.stdout", new_callable=StringIO) as stdout:
                            result = CHIYO.run_tool(
                                "bm",
                                ["--print-url", "Example"],
                            )

        self.assertEqual(result, "https://example.test")
        self.assertEqual(stdout.getvalue(), "https://example.test\n")

    def test_run_tool_runs_builtin_zo_default_open(self):
        item = {
            "key": "ITEMKEY1",
            "library_type": "user",
            "title": "Linear Algebra Done Right",
            "creators": "Sheldon Axler",
            "date": "2015",
            "item_type": "book",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_config_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        'tool_dirs = []',
                        'enabled_tools = ["jingke-zhang/zotero"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_config_path):
                    with mock.patch("chiyo_cli.builtin_tools.zotero.tool.load_items") as load_items:
                        with mock.patch("chiyo_cli.builtin_tools.zotero.tool.open_location") as open_location:
                            load_items.return_value = [item]
                            result = CHIYO.run_tool("zo", ["linear"])

        self.assertEqual(result, "zotero://select/library/items/ITEMKEY1")
        open_location.assert_called_once()
        self.assertEqual(
            open_location.call_args.args[0],
            "zotero://select/library/items/ITEMKEY1",
        )

    def test_shell_tool_lines_runs_builtin_proj(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "My Project"
            project.mkdir()
            config_path = os.path.join(temp_dir, "config.toml")
            tools_config_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        'tool_dirs = []',
                        'enabled_tools = ["jingke-zhang/project"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_config_path):
                    with mock.patch("chiyo_cli.builtin_tools.project.all_projects") as all_projects:
                        with mock.patch("chiyo_cli.builtin_tools.project.normalize_roots") as normalize_roots:
                            normalize_roots.return_value = [temp_dir]
                            all_projects.return_value = [str(project)]
                            lines = CHIYO.shell_tool_lines("proj", ["Project"])

        self.assertEqual(lines, [ShellAction.cd(str(project)).render_shell()])

    def test_shell_tool_lines_runs_builtin_gop_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "Target Dir"
            target.mkdir()
            config_path = os.path.join(temp_dir, "config.toml")
            tools_config_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        'tool_dirs = []',
                        'enabled_tools = ["jingke-zhang/go-or-pick"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )
            Path(tools_config_path).write_text(
                f'["jingke-zhang/go-or-pick"]\nroots = ["{temp_dir}"]\nexclude = []\nfzf_prompt = "gop> "\n',
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_config_path):
                    with mock.patch("chiyo_cli.builtin_tools.go_or_pick.run_fd") as run_fd:
                        run_fd.return_value = [str(target)]
                        lines = CHIYO.shell_tool_lines("gop", ["Target"])

        self.assertEqual(lines, [ShellAction.cd(str(target)).render_shell()])

    def test_shell_tool_lines_expands_gop_config_roots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir)
            root = home / "Documents"
            root.mkdir()
            target = root / "Target Dir"
            target.mkdir()
            config_path = os.path.join(temp_dir, "config.toml")
            tools_config_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        'tool_dirs = []',
                        'enabled_tools = ["jingke-zhang/go-or-pick"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )
            Path(tools_config_path).write_text(
                '["jingke-zhang/go-or-pick"]\nroots = ["~/Documents"]\nexclude = []\nfzf_prompt = "gop> "\n',
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_config_path):
                    with mock.patch.dict(os.environ, {"HOME": str(home)}):
                        with mock.patch("chiyo_cli.builtin_tools.go_or_pick.run_fd") as run_fd:
                            run_fd.return_value = [str(target)]
                            lines = CHIYO.shell_tool_lines("gop", ["Target"])

        self.assertEqual(lines, [ShellAction.cd(str(target)).render_shell()])
        self.assertEqual(run_fd.call_args.args[1], [str(root)])

    def test_shell_tool_lines_runs_builtin_gop_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "paper.pdf"
            target.write_text("pdf", encoding="utf-8")
            config_path = os.path.join(temp_dir, "config.toml")
            tools_config_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        'tool_dirs = []',
                        'enabled_tools = ["jingke-zhang/go-or-pick"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )
            Path(tools_config_path).write_text(
                f'["jingke-zhang/go-or-pick"]\nroots = ["{temp_dir}"]\nexclude = []\nfzf_prompt = "gop> "\n',
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_config_path):
                    with mock.patch("chiyo_cli.builtin_tools.go_or_pick.run_fd") as run_fd:
                        run_fd.return_value = [str(target)]
                        lines = CHIYO.shell_tool_lines("gop", ["paper"])

        self.assertEqual(lines, [ShellAction.open(str(target)).render_shell()])

    def test_tool_doc_lines_returns_builtin_docs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        'tool_dirs = []',
                        'enabled_tools = []',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                lines = CHIYO.tool_doc_lines("s")

        self.assertIn("# s", "\n".join(lines))

    def test_user_tool_doctor_checks_report_metadata_and_install_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper_dir = Path(temp_dir) / "bin"
            wrapper_dir.mkdir()
            completion_dir = Path(temp_dir) / "zsh"
            completion_dir.mkdir()
            (wrapper_dir / "paper").write_text(
                CHIYO.wrapper_script("paper"),
                encoding="utf-8",
            )
            (completion_dir / "_paper").write_text(
                CHIYO.completion_script("paper"),
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

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                lines = [
                    f"{status:7} {label}: {detail}"
                    for status, detail, label in CHIYO.user_tool_doctor_checks()
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

    def test_user_tool_doctor_checks_warn_when_installed_completion_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper_dir = Path(temp_dir) / "bin"
            wrapper_dir.mkdir()
            completion_dir = Path(temp_dir) / "zsh"
            (wrapper_dir / "paper").write_text(
                CHIYO.wrapper_script("paper"),
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

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                lines = [
                    f"{status:7} {label}: {detail}"
                    for status, detail, label in CHIYO.user_tool_doctor_checks()
                ]

        self.assertIn(
            f"warn    user tool fixture/paper-search zsh: {completion_dir / '_paper'} not found",
            "\n".join(lines),
        )


if __name__ == "__main__":
    unittest.main()
