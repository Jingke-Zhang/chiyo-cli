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


class RunDispatchTests(unittest.TestCase):
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

    def test_run_tool_allows_disabled_tool_help(self):
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
                with mock.patch("sys.stdout", new_callable=StringIO):
                    with self.assertRaises(SystemExit) as context:
                        CHIYO.run_tool("paper", ["--help"])

        self.assertEqual(context.exception.code, 0)

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

    def test_shell_tool_lines_runs_builtin_agd_terminal_open(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_config_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        "tool_dirs = []",
                        'enabled_tools = ["jingke-zhang/agenda"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )
            Path(tools_config_path).write_text(
                "\n".join(
                    [
                        '["jingke-zhang/agenda"]',
                        'emacsclient_open_args = ["-nw"]',
                    ]
                ),
                encoding="utf-8",
            )
            item = {
                "todo": "TODO",
                "title": "Write release notes",
                "agenda": "todo: TODO Write release notes",
                "category": "chiyo",
                "file": "/tmp/chiyo/tasks.org",
                "line": 42,
                "column": 3,
            }

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_config_path):
                    with mock.patch(
                        "chiyo_cli.builtin_tools.agenda.agenda_items",
                        return_value=[item],
                    ):
                        with mock.patch("chiyo_cli.builtin_tools.agenda.require_command"):
                            lines = CHIYO.shell_tool_lines("agd", ["release"])

        self.assertEqual(lines, ["emacsclient -nw +42:3 /tmp/chiyo/tasks.org"])

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


if __name__ == "__main__":
    unittest.main()
