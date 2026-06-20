import tempfile
import unittest
from pathlib import Path

from chiyo_cli.config import init_module_config, load_minimal_toml, load_module_config


class ConfigTests(unittest.TestCase):
    def test_init_module_config_preserves_other_modules(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                "\n".join(
                    [
                        "[other]",
                        'name = "kept"',
                        "",
                        "[bm]",
                        'browser = "Firefox"',
                        "",
                        "[bm.rename_folders]",
                        'BookmarksBar = "Old"',
                    ]
                ),
                encoding="utf-8",
            )

            init_module_config(
                "bm",
                {"browser": "Safari", "skip_folders": ["Bookmarks"]},
                config_path=str(config_path),
            )

            self.assertEqual(
                config_path.read_text(encoding="utf-8"),
                "\n".join(
                    [
                        "[other]",
                        'name = "kept"',
                        "",
                        "[bm]",
                        'browser = "Safari"',
                        'skip_folders = ["Bookmarks"]',
                        "",
                    ]
                ),
            )

    def test_load_module_config_uses_defaults_when_module_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text("[other]\nname = \"kept\"\n", encoding="utf-8")

            config = load_module_config(
                "bm",
                {"browser": "Safari", "skip_folders": ["Bookmarks"]},
                config_path=str(config_path),
            )

            self.assertEqual(
                config,
                {"browser": "Safari", "skip_folders": ["Bookmarks"]},
            )

    def test_load_module_config_does_not_merge_configured_collections(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                "\n".join(
                    [
                        "[bm]",
                        'browser = "Firefox"',
                        "",
                        'skip_folders = ["Custom"]',
                    ]
                ),
                encoding="utf-8",
            )

            config = load_module_config(
                "bm",
                {"browser": "Safari", "skip_folders": ["Bookmarks"]},
                config_path=str(config_path),
            )

            self.assertEqual(config["browser"], "Firefox")
            self.assertEqual(config["skip_folders"], ["Custom"])

    def test_load_module_config_warns_when_configured_module_uses_default_fallback(self):
        warnings = []

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text("[bm]\n", encoding="utf-8")

            config = load_module_config(
                "bm",
                {"browser": "Safari"},
                config_path=str(config_path),
                warn=warnings.append,
            )

            self.assertEqual(config["browser"], "Safari")
            self.assertEqual(
                warnings,
                ["config [bm] missing browser; using default."],
            )

    def test_init_module_config_writes_empty_nested_tables(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"

            init_module_config(
                "app",
                {"fzf_prompt": "app> ", "alias": {}},
                config_path=str(config_path),
            )

            self.assertEqual(
                config_path.read_text(encoding="utf-8"),
                "\n".join(
                    [
                        "[app]",
                        'fzf_prompt = "app> "',
                        "",
                        "[app.alias]",
                        "",
                    ]
                ),
            )

    def test_load_minimal_toml_accepts_shell_escaped_spaces(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                "\n".join(
                    [
                        "[gop]",
                        'roots = ["~/OneDrive\\ -\\ The\\ University\\ of\\ Tokyo"]',
                        "bare = true",
                    ]
                ),
                encoding="utf-8",
            )

            config = load_minimal_toml(str(config_path))

        self.assertEqual(
            config["gop"]["roots"],
            ["~/OneDrive - The University of Tokyo"],
        )
        self.assertTrue(config["gop"]["bare"])


if __name__ == "__main__":
    unittest.main()
