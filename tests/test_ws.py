import subprocess
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
WS = SourceFileLoader("ws", str(REPO_ROOT / "bin" / "ws")).load_module()


class WsTests(unittest.TestCase):
    def test_parse_search_uses_engine_when_first_term_matches(self):
        engines = {"g": {"name": "Google", "url": "https://example?q={query}"}}

        self.assertEqual(
            WS.parse_search(["g", "wavelet", "tree"], engines),
            ("g", "wavelet tree"),
        )

    def test_parse_search_force_interactive_treats_engine_as_query(self):
        engines = {"g": {"name": "Google", "url": "https://example?q={query}"}}

        self.assertEqual(
            WS.parse_search(["g", "wavelet", "tree"], engines, True),
            (None, "g wavelet tree"),
        )

    def test_build_search_url_url_encodes_query(self):
        engine = {"name": "Google", "url": "https://google.test/search?q={query}"}

        self.assertEqual(
            WS.build_search_url(engine, "wavelet tree"),
            "https://google.test/search?q=wavelet%20tree",
        )

    @mock.patch("ws.choose_item")
    def test_choose_engine_returns_selected_key(self, choose_item):
        engines = {
            "g": {"name": "Google", "url": "https://google.test?q={query}"},
            "gh": {"name": "GitHub", "url": "https://github.test?q={query}"},
        }
        choose_item.return_value = ("gh", engines["gh"])

        self.assertEqual(WS.choose_engine(engines, {"fzf_prompt": "ws> "}), "gh")

    @mock.patch("ws.shutil.which", return_value="/usr/bin/open")
    @mock.patch("ws.subprocess.run")
    def test_open_url_uses_macos_open(self, run, _which):
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr="",
        )

        WS.open_url("https://example.test")

        self.assertEqual(run.call_args.args[0], ["open", "https://example.test"])

    def test_load_config_reads_nested_engines(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                "\n".join(
                    [
                        "[ws]",
                        'fzf_prompt = "ws> "',
                        "",
                        "[ws.engines.g]",
                        'name = "Google"',
                        'url = "https://google.test/search?q={query}"',
                    ]
                ),
                encoding="utf-8",
            )

            config = WS.load_module_config(
                "ws",
                WS.DEFAULT_CONFIG,
                config_path=str(config_path),
            )

            self.assertEqual(config["engines"]["g"]["name"], "Google")

    def test_init_config_replaces_ws_tables_and_preserves_other_modules(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.toml"
            path.write_text(
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
            with mock.patch.object(WS, "CONFIG_PATH", str(path)):
                WS.init_config()

            content = path.read_text(encoding="utf-8")
            self.assertIn("[other]", content)
            self.assertIn('name = "kept"', content)
            self.assertIn("[ws.engines.g]", content)
            self.assertNotIn("[ws.engines.old]", content)


if __name__ == "__main__":
    unittest.main()
