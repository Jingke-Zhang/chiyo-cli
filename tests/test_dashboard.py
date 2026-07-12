import os
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock

from chiyo_cli import cli as CHIYO
from chiyo_cli.commands import dashboard as DASHBOARD


class DashboardTests(unittest.TestCase):
    def test_dashboard_lines_show_enabled_tools(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_config_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        "tool_dirs = []",
                        'enabled_tools = ["shiori-route/web-search"]',
                        f'wrapper_dir = "{temp_dir}/bin"',
                        f'completion_dir = "{temp_dir}/zsh"',
                    ]
                ),
                encoding="utf-8",
            )
            Path(tools_config_path).write_text(
                "\n".join(
                    [
                        '["shiori-route/web-search"]',
                        'cmds = ["s", "search"]',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(DASHBOARD, "CONFIG_PATH", config_path):
                with mock.patch.object(DASHBOARD, "TOOLS_CONFIG_PATH", tools_config_path):
                    lines = DASHBOARD.dashboard_lines()

        output = "\n".join(lines)
        self.assertIn("Chiyo CLI", output)
        self.assertIn("enabled tools: 1", output)
        self.assertIn("Web Search", output)
        self.assertIn("s, search", output)
        self.assertIn("chiyo tool list", output)

    def test_main_without_args_prints_dashboard(self):
        with mock.patch("chiyo_cli.cli.dashboard") as dashboard:
            CHIYO.main([])

        dashboard.assert_called_once_with()

    def test_dashboard_prints_lines(self):
        with mock.patch.object(DASHBOARD, "dashboard_lines") as dashboard_lines:
            dashboard_lines.return_value = ["Chiyo CLI", "Manage"]

            with mock.patch("sys.stdout", new_callable=StringIO) as stdout:
                DASHBOARD.dashboard()

        self.assertEqual(stdout.getvalue(), "Chiyo CLI\nManage\n")


if __name__ == "__main__":
    unittest.main()
