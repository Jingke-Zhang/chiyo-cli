import os
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock

from chiyo_cli import cli as CHIYO


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_TOOL_DIR = REPO_ROOT / "tests" / "fixtures" / "user_tools"


class ToolCliTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
