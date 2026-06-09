import subprocess
import tempfile
import unittest
from io import StringIO
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
        self.assertEqual(choose_item.call_args.kwargs["search_display_fields"], [1, 2])
        self.assertNotIn("filter_rows", choose_item.call_args.kwargs)

    def test_list_completions_prints_engine_keys(self):
        config = {
            "engines": {
                "scholar": {"name": "Scholar", "url": "https://s.test?q={query}"},
                "g": {"name": "Google", "url": "https://g.test?q={query}"},
            }
        }

        with mock.patch("sys.stdout", new_callable=StringIO) as stdout:
            WS.list_completions(config)

        self.assertEqual(stdout.getvalue(), "scholar\ng\n")

    @mock.patch("ws.open_url")
    @mock.patch("ws.load_config")
    def test_main_lists_completions_without_opening_url(self, load_config, open_url):
        load_config.return_value = {
            "engines": {
                "g": {"name": "Google", "url": "https://g.test?q={query}"},
            }
        }

        with mock.patch("sys.stdout", new_callable=StringIO) as stdout:
            WS.main(["--list-completions"])

        self.assertEqual(stdout.getvalue(), "g\n")
        open_url.assert_not_called()

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

    def test_load_config_does_not_merge_default_engines_when_ws_is_configured(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.toml"
            path.write_text(
                "\n".join(
                    [
                        "[ws]",
                        'fzf_prompt = "ws> "',
                        "",
                        "[ws.engines.custom]",
                        'name = "Custom"',
                        'url = "https://custom.test/search?q={query}"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(WS, "CONFIG_PATH", str(path)):
                config = WS.load_config()

            self.assertEqual(list(config["engines"]), ["custom"])

    def test_load_config_warns_when_ws_uses_default_engines_fallback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.toml"
            path.write_text("[ws]\nfzf_prompt = \"ws> \"\n", encoding="utf-8")

            with mock.patch.object(WS, "CONFIG_PATH", str(path)):
                with mock.patch("ws.warn") as warn:
                    config = WS.load_config()

            self.assertIn("g", config["engines"])
            warn.assert_called_once_with("config [ws] missing engines; using default.")

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
