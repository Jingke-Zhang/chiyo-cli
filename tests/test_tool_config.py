import tempfile
import unittest
from pathlib import Path

from chiyo_cli.tool_config import (
    DEFAULT_CHIYO_CONFIG,
    disable_tool,
    enable_tool,
    format_chiyo_config,
    init_chiyo_config,
    init_tool_config,
    load_chiyo_config,
    load_tool_config,
    load_tools_config,
)


class ToolConfigTests(unittest.TestCase):
    def test_load_chiyo_config_uses_infrastructure_defaults(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"

            config = load_chiyo_config(config_path=str(config_path))

        self.assertEqual(config["enabled_tools"], ["chiyo/gop", "chiyo/ws"])
        self.assertTrue(config["tool_dirs"][0].endswith(".config/chiyo-cli/tools"))
        self.assertTrue(config["wrapper_dir"].endswith(".local/bin"))

    def test_load_chiyo_config_expands_paths_from_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        'tool_dirs = ["~/Tools"]',
                        'enabled_tools = ["paper"]',
                        'wrapper_dir = "~/bin"',
                        'completion_dir = "~/zsh"',
                    ]
                ),
                encoding="utf-8",
            )

            config = load_chiyo_config(config_path=str(config_path))

        self.assertEqual(config["enabled_tools"], ["paper"])
        self.assertNotIn("~", config["tool_dirs"][0])
        self.assertNotIn("~", config["wrapper_dir"])
        self.assertNotIn("~", config["completion_dir"])

    def test_tools_config_is_loaded_from_separate_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tools_path = Path(temp_dir) / "tools.toml"
            tools_path.write_text(
                "\n".join(
                    [
                        "[paper]",
                        'root = "~/Papers"',
                    ]
                ),
                encoding="utf-8",
            )

            config = load_tools_config(config_path=str(tools_path))

        self.assertEqual(config["paper"]["root"], "~/Papers")

    def test_load_tool_config_reads_tool_defaults_from_tools_toml(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tools_path = Path(temp_dir) / "tools.toml"
            tools_path.write_text(
                "\n".join(
                    [
                        "[paper]",
                        'root = "~/Library/Papers"',
                    ]
                ),
                encoding="utf-8",
            )

            config = load_tool_config(
                "paper",
                {"root": "~/Papers", "fzf_prompt": "paper> "},
                config_path=str(tools_path),
            )

        self.assertEqual(config["root"], "~/Library/Papers")
        self.assertEqual(config["fzf_prompt"], "paper> ")

    def test_init_helpers_write_separate_config_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            tools_path = Path(temp_dir) / "tools.toml"

            init_chiyo_config(config_path=str(config_path))
            init_tool_config(
                "paper",
                {"root": "~/Papers"},
                config_path=str(tools_path),
            )

            config_text = config_path.read_text(encoding="utf-8")
            tools_text = tools_path.read_text(encoding="utf-8")

        self.assertIn("[chiyo]", config_text)
        self.assertIn("[paper]", tools_text)
        self.assertNotIn("[paper]", config_text)
        self.assertNotIn("[chiyo]", tools_text)

    def test_format_chiyo_config_renders_defaults(self):
        text = format_chiyo_config()

        self.assertIn("[chiyo]", text)
        self.assertIn("enabled_tools", text)
        self.assertIn(DEFAULT_CHIYO_CONFIG["wrapper_dir"], text)

    def test_enable_tool_adds_command_once(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"

            enable_tool("paper", config_path=str(config_path))
            enable_tool("paper", config_path=str(config_path))

            config = load_chiyo_config(config_path=str(config_path))

        self.assertEqual(config["enabled_tools"], ["chiyo/gop", "chiyo/ws", "paper"])

    def test_disable_tool_removes_command_and_reports_previous_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"

            enable_tool("paper", config_path=str(config_path))
            self.assertTrue(disable_tool("paper", config_path=str(config_path)))
            self.assertFalse(disable_tool("paper", config_path=str(config_path)))

            config = load_chiyo_config(config_path=str(config_path))

        self.assertEqual(config["enabled_tools"], ["chiyo/gop", "chiyo/ws"])


if __name__ == "__main__":
    unittest.main()
