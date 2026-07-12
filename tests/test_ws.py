import subprocess
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock

from chiyo_cli.builtin_tools import web_search as WS
from chiyo_cli.config import format_module_config
from chiyo_cli.tool_config import load_tool_config


class WsTests(unittest.TestCase):
    def test_parse_search_uses_engine_when_first_term_matches(self):
        engines = {"g": {"name": "Google", "url": "https://example?q={query}"}}
        tool = WS.Tool()
        tool._engine_keys = set(engines)

        self.assertEqual(
            tool.query_from_args(tool.parser().parse_args(["g", "wavelet", "tree"])),
            "wavelet tree",
        )
        self.assertEqual(tool._selected_engine, "g")

    def test_parse_search_without_engine_treats_terms_as_query(self):
        engines = {"g": {"name": "Google", "url": "https://example?q={query}"}}
        tool = WS.Tool()
        tool._engine_keys = set(engines)

        self.assertEqual(
            tool.query_from_args(tool.parser().parse_args(["gh", "wavelet", "tree"])),
            "gh wavelet tree",
        )
        self.assertIsNone(tool._selected_engine)

    def test_build_search_url_url_encodes_query(self):
        engine = {"name": "Google", "url": "https://google.test/search?q={query}"}

        self.assertEqual(
            WS.build_search_url(engine, "wavelet tree"),
            "https://google.test/search?q=wavelet%20tree",
        )

    @mock.patch("chiyo_cli.fzf.choose_item")
    def test_choose_engine_returns_selected_key(self, choose_item):
        engines = {
            "g": {"name": "Google", "url": "https://google.test?q={query}"},
            "gh": {"name": "GitHub", "url": "https://github.test?q={query}"},
        }
        choose_item.return_value = {
            "key": "gh",
            "name": "GitHub",
            "url": "https://github.test?q={query}",
        }

        tool = WS.Tool()
        selected = tool.select_item(
            tool.items({"engines": engines}),
            "",
            tool.parser().parse_args([]),
            {"fzf_prompt": "s> ", "engines": engines},
        )

        self.assertEqual(selected["key"], "gh")
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
            WS.Tool().print_completions(config)

        self.assertEqual(stdout.getvalue(), "scholar\ng\n")

    @mock.patch("chiyo_cli.toolkit.open_location")
    def test_run_lists_completions_without_opening_url(self, open_location):
        config = {
            "fzf_prompt": "s> ",
            "engines": {
                "g": {"name": "Google", "url": "https://g.test?q={query}"},
            }
        }

        with mock.patch("sys.stdout", new_callable=StringIO) as stdout:
            WS.Tool().run(["--list-completions"], config=config)

        self.assertEqual(stdout.getvalue(), "g\n")
        open_location.assert_not_called()

    @mock.patch("chiyo_cli.toolkit.shutil.which", return_value="/usr/bin/open")
    @mock.patch("chiyo_cli.toolkit.subprocess.run")
    def test_open_url_uses_macos_open(self, run, _which):
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr="",
        )

        WS.Tool().open_url("https://example.test")

        self.assertEqual(run.call_args.args[0], ["open", "https://example.test"])

    def test_load_config_reads_nested_engines(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                "\n".join(
                    [
                        '["shiori-route/web-search"]',
                        'fzf_prompt = "s> "',
                        "",
                        '["shiori-route/web-search".engines.g]',
                        'name = "Google"',
                        'url = "https://google.test/search?q={query}"',
                    ]
                ),
                encoding="utf-8",
            )

            config = load_tool_config(
                "shiori-route/web-search",
                WS.Tool.default_config,
                config_path=str(config_path),
            )

            self.assertEqual(config["engines"]["g"]["name"], "Google")

    def test_load_config_does_not_merge_default_engines_when_ws_is_configured(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.toml"
            path.write_text(
                "\n".join(
                    [
                        '["shiori-route/web-search"]',
                        'fzf_prompt = "s> "',
                        "",
                        '["shiori-route/web-search".engines.custom]',
                        'name = "Custom"',
                        'url = "https://custom.test/search?q={query}"',
                    ]
                ),
                encoding="utf-8",
            )

            config = load_tool_config("shiori-route/web-search", WS.Tool.default_config, config_path=str(path))

            self.assertEqual(list(config["engines"]), ["custom"])

    def test_load_config_warns_when_ws_uses_default_engines_fallback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.toml"
            path.write_text('["shiori-route/web-search"]\nfzf_prompt = "s> "\n', encoding="utf-8")

            warn = mock.Mock()
            config = load_tool_config(
                "shiori-route/web-search",
                WS.Tool.default_config,
                config_path=str(path),
                warn=warn,
            )

            self.assertIn("g", config["engines"])
            warn.assert_called_once_with("config [shiori-route/web-search] missing engines; using default.")

    def test_format_default_config_includes_default_engines(self):
        content = format_module_config("shiori-route/web-search", WS.Tool.default_config)

        self.assertIn('["shiori-route/web-search"]', content)
        self.assertIn('["shiori-route/web-search".engines.g]', content)


if __name__ == "__main__":
    unittest.main()
