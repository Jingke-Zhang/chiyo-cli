import tempfile
import unittest
from pathlib import Path

from chiyo_cli.config import init_module_config, load_module_config


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

    def test_load_module_config_merges_defaults_and_config_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                "\n".join(
                    [
                        "[bm]",
                        'browser = "Firefox"',
                        "",
                        "[bm.rename_folders]",
                        'BookmarksBar = "Personal"',
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
            self.assertEqual(config["skip_folders"], ["Bookmarks"])
            self.assertEqual(config["rename_folders"], {"BookmarksBar": "Personal"})


if __name__ == "__main__":
    unittest.main()
