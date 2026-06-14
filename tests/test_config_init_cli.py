import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from chiyo_cli import cli as CHIYO


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_TOOL_DIR = REPO_ROOT / "tests" / "fixtures" / "user_tools"


class ConfigInitCliTests(unittest.TestCase):
    def test_validate_config_init_requires_target(self):
        args = mock.Mock(all=False, tools=[])

        with self.assertRaises(ValueError):
            CHIYO.validate_config_init_args(args)

    def test_config_init_all_write_writes_every_tool_when_config_is_empty(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_path = os.path.join(temp_dir, "tools.toml")

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_path):
                    targets = CHIYO.validate_config_init_args(
                        mock.Mock(all=True, tools=[])
                    )
                    lines = CHIYO.config_init_lines(targets, "write")

            config_content = Path(config_path).read_text(encoding="utf-8")
            tools_content = Path(tools_path).read_text(encoding="utf-8")

        self.assertIn("wrote [chiyo] config", "\n".join(lines))
        self.assertIn("wrote [jingke-zhang/go-or-pick] config", "\n".join(lines))
        self.assertIn("wrote [jingke-zhang/web-search] config", "\n".join(lines))
        self.assertIn("wrote [jingke-zhang/workspace] config", "\n".join(lines))
        self.assertIn("[chiyo]", config_content)
        self.assertIn('enabled_tools = ["jingke-zhang/go-or-pick", "jingke-zhang/web-search", "jingke-zhang/workspace"]', config_content)
        self.assertNotIn("[ws]", config_content)
        self.assertIn('["jingke-zhang/go-or-pick"]', tools_content)
        self.assertIn('["jingke-zhang/web-search".engines.g]', tools_content)
        self.assertIn('["jingke-zhang/workspace"]', tools_content)
        self.assertNotIn("[bm]", tools_content)

    def test_config_init_all_uses_current_enabled_tools(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                '[chiyo]\nenabled_tools = ["jingke-zhang/explorer-bookmark", "jingke-zhang/zotero"]\n',
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_path):
                    targets = CHIYO.validate_config_init_args(
                        mock.Mock(all=True, tools=[])
                    )
                    lines = CHIYO.config_init_lines(targets, "append")

            tools_content = Path(tools_path).read_text(encoding="utf-8")

        self.assertEqual(["chiyo", "jingke-zhang/explorer-bookmark", "jingke-zhang/zotero"], targets)
        self.assertIn("append [chiyo] defaults", "\n".join(lines))
        self.assertIn("append [jingke-zhang/explorer-bookmark] config", "\n".join(lines))
        self.assertIn("append [jingke-zhang/zotero] config", "\n".join(lines))
        self.assertIn('["jingke-zhang/explorer-bookmark"]', tools_content)
        self.assertIn('["jingke-zhang/zotero"]', tools_content)
        self.assertNotIn("[gop]", tools_content)
        self.assertNotIn("[ws]", tools_content)

    def test_config_init_write_refuses_non_empty_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_path = os.path.join(temp_dir, "tools.toml")
            Path(tools_path).write_text("[other]\n", encoding="utf-8")

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_path):
                    with self.assertRaises(CHIYO.ConfigInitRefused):
                        CHIYO.config_init_lines(["s"], "write")

    def test_config_init_append_skips_existing_and_adds_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_path = os.path.join(temp_dir, "tools.toml")
            Path(tools_path).write_text("[ws]\nfzf_prompt = \"old> \"\n", encoding="utf-8")

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_path):
                    lines = CHIYO.config_init_lines(["s", "app"], "append")

            content = Path(tools_path).read_text(encoding="utf-8")

        self.assertIn("append [jingke-zhang/web-search] config", "\n".join(lines))
        self.assertIn("append [jingke-zhang/application] config", "\n".join(lines))
        self.assertIn('["jingke-zhang/application".alias]', content)
        self.assertIn('["jingke-zhang/web-search".engines.g]', content)
        self.assertIn('fzf_prompt = "old> "', content)

    def test_config_init_append_adds_missing_bm_defaults(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_path = os.path.join(temp_dir, "tools.toml")
            Path(tools_path).write_text(
                "\n".join(
                    [
                        "[bm]",
                        'skip_folders = ["Bookmarks"]',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_path):
                    lines = CHIYO.config_init_lines(["bm"], "append")

            content = Path(tools_path).read_text(encoding="utf-8")

        self.assertIn("append [jingke-zhang/explorer-bookmark] config", "\n".join(lines))
        self.assertIn('skip_folders = ["Bookmarks"]', content)
        self.assertIn('["jingke-zhang/explorer-bookmark"]', content)

    def test_config_init_append_preserves_existing_bm_defaults(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_path = os.path.join(temp_dir, "tools.toml")
            Path(tools_path).write_text(
                "\n".join(
                    [
                        "[bm]",
                        'bookmarks_path = "~/Bookmarks.plist"',
                        'skip_folders = ["Bookmarks"]',
                        'fzf_prompt = "bookmarks> "',
                        'browser = "Google Chrome"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_path):
                    lines = CHIYO.config_init_lines(["bm"], "append")

            content = Path(tools_path).read_text(encoding="utf-8")

        self.assertIn("append [jingke-zhang/explorer-bookmark] config", "\n".join(lines))
        self.assertIn('bookmarks_path = "~/Bookmarks.plist"', content)
        self.assertIn('fzf_prompt = "bookmarks> "', content)
        self.assertIn('browser = "Google Chrome"', content)
        self.assertIn('["jingke-zhang/explorer-bookmark"]', content)

    def test_config_init_force_replaces_selected_tool(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_path = os.path.join(temp_dir, "tools.toml")
            Path(tools_path).write_text(
                "\n".join(
                    [
                        "[other]",
                        'name = "kept"',
                        "",
                        "[ws]",
                        'fzf_prompt = "old> "',
                        "",
                        "[ws.engines.old]",
                        'name = "Old"',
                        'url = "https://old.test?q={query}"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_path):
                    CHIYO.config_init_lines(["s"], "force")

            content = Path(tools_path).read_text(encoding="utf-8")

        self.assertIn("[other]", content)
        self.assertIn('["jingke-zhang/web-search".engines.g]', content)
        self.assertIn("[ws.engines.old]", content)

if __name__ == "__main__":
    unittest.main()
