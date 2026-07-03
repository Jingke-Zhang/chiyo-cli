import json
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock

from chiyo_cli.builtin_tools import dictionary as DICT


class DictionaryTests(unittest.TestCase):
    def test_personal_entry_prefers_language_pair(self):
        config = {
            "entries": {
                "epistemic": {
                    "meaning": "relating to knowledge",
                    "en-zh": "认识论的",
                    "note": "Often used in epistemic uncertainty.",
                }
            }
        }

        content = DICT.personal_entry(config, "epistemic", "en", "zh")

        self.assertIn("en -> zh", content)
        self.assertIn("认识论的", content)
        self.assertIn("epistemic uncertainty", content)

    def test_format_dictionaryapi_renders_definitions(self):
        content = DICT.format_dictionaryapi(
            "test",
            "en",
            [
                {
                    "phonetics": [{"text": "/test/"}],
                    "meanings": [
                        {
                            "partOfSpeech": "noun",
                            "definitions": [
                                {
                                    "definition": "A procedure for discovery.",
                                    "example": "Run a test.",
                                }
                            ],
                        }
                    ],
                }
            ],
        )

        self.assertIn("# test", content)
        self.assertIn("Pronunciation: /test/", content)
        self.assertIn("## noun", content)
        self.assertIn("1. A procedure for discovery.", content)
        self.assertIn("Example: Run a test.", content)

    def test_format_jisho_renders_japanese_entries(self):
        content = DICT.format_jisho(
            "言葉",
            {
                "data": [
                    {
                        "japanese": [{"word": "言葉", "reading": "ことば"}],
                        "senses": [
                            {
                                "parts_of_speech": ["Noun"],
                                "english_definitions": ["word", "language"],
                            }
                        ],
                    }
                ]
            },
        )

        self.assertIn("# 言葉", content)
        self.assertIn("ja -> ja", content)
        self.assertIn("## 言葉 [ことば]", content)
        self.assertIn("- (Noun) word; language", content)

    @mock.patch("chiyo_cli.builtin_tools.dictionary.http_json")
    def test_lookup_online_uses_dictionary_for_same_language(self, http_json):
        http_json.return_value = [
            {
                "meanings": [
                    {
                        "partOfSpeech": "adjective",
                        "definitions": [{"definition": "Known by experience."}],
                    }
                ]
            }
        ]

        content = DICT.lookup_online("empirical", "en", "en", 5)

        self.assertIn("Known by experience.", content)
        self.assertIn("/api/v2/entries/en/empirical", http_json.call_args.args[0])
        self.assertEqual(http_json.call_args.args[1], 5)

    @mock.patch("chiyo_cli.builtin_tools.dictionary.http_json")
    def test_lookup_online_uses_translation_for_different_language(self, http_json):
        http_json.return_value = {
            "responseData": {
                "translatedText": "经验的",
            }
        }

        content = DICT.lookup_online("empirical", "en", "zh", 5)

        self.assertIn("en -> zh", content)
        self.assertIn("经验的", content)
        self.assertIn("langpair=en|zh-CN", http_json.call_args.args[0])

    @mock.patch("chiyo_cli.builtin_tools.dictionary.http_json")
    def test_lookup_online_uses_jisho_for_japanese_definitions(self, http_json):
        http_json.return_value = {
            "data": [
                {
                    "japanese": [{"word": "言葉", "reading": "ことば"}],
                    "senses": [{"english_definitions": ["word"]}],
                }
            ]
        }

        content = DICT.lookup_online("言葉", "ja", "ja", 5)

        self.assertIn("ja -> ja", content)
        self.assertIn("word", content)
        self.assertIn("jisho.org/api/v1/search/words", http_json.call_args.args[0])

    @mock.patch("chiyo_cli.builtin_tools.dictionary.http_json")
    def test_lookup_online_maps_ja_zh_en_translation_pairs(self, http_json):
        http_json.return_value = {
            "responseData": {
                "translatedText": "translated",
            }
        }

        pairs = [
            ("ja", "zh", "langpair=ja|zh-CN"),
            ("zh", "ja", "langpair=zh-CN|ja"),
            ("ja", "en", "langpair=ja|en"),
            ("en", "ja", "langpair=en|ja"),
            ("zh", "en", "langpair=zh-CN|en"),
            ("en", "zh", "langpair=en|zh-CN"),
        ]

        for input_language, output_language, expected_url in pairs:
            with self.subTest(pair=(input_language, output_language)):
                DICT.lookup_online("term", input_language, output_language, 5)
                self.assertIn(expected_url, http_json.call_args.args[0])

    @mock.patch("chiyo_cli.builtin_tools.dictionary.http_json")
    def test_lookup_online_accepts_language_aliases(self, http_json):
        http_json.return_value = {
            "responseData": {
                "translatedText": "translated",
            }
        }

        DICT.lookup_online("term", "jp", "zh-cn", 5)

        self.assertIn("langpair=ja|zh-CN", http_json.call_args.args[0])

    def test_cache_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = dict(DICT.DEFAULT_CONFIG)
            config["cache_path"] = str(Path(temp_dir) / "dictionary.sqlite3")

            DICT.write_cache(config, "Empirical", "en", "zh", "cached")

            self.assertEqual(
                DICT.read_cache(config, "empirical", "EN", "ZH"),
                "cached",
            )

    @mock.patch("chiyo_cli.builtin_tools.dictionary.lookup")
    def test_run_uses_language_flags_and_prints_without_viewer(self, lookup):
        lookup.return_value = "# empirical\n\n经验的\n"

        with mock.patch("sys.stdout", new_callable=StringIO) as stdout:
            result = DICT.Tool().run(
                ["-i", "en", "-o", "zh", "empirical"],
                config=DICT.DEFAULT_CONFIG,
                execute_shell_actions=False,
            )

        self.assertEqual(result, "# empirical\n\n经验的\n")
        self.assertEqual(stdout.getvalue(), "# empirical\n\n经验的\n")
        lookup.assert_called_once()
        self.assertEqual(lookup.call_args.args[:3], ("empirical", "en", "zh"))

    @mock.patch("chiyo_cli.builtin_tools.dictionary.subprocess.run")
    def test_render_content_uses_configured_viewer(self, run):
        run.return_value = mock.Mock(returncode=0)
        config = dict(DICT.DEFAULT_CONFIG)
        config["viewer"] = ["cat"]

        DICT.render_content("hello\n", config)

        run.assert_called_once_with(
            ["cat"],
            input="hello\n",
            text=True,
            check=False,
        )

    def test_viewer_command_splits_string_viewer(self):
        config = dict(DICT.DEFAULT_CONFIG)
        config["viewer"] = "glow -s light"

        self.assertEqual(DICT.viewer_command(config), ["glow", "-s", "light"])

    def test_viewer_command_splits_pager(self):
        config = dict(DICT.DEFAULT_CONFIG)
        config["viewer"] = []

        with mock.patch.dict("os.environ", {"PAGER": "glow -s light"}):
            self.assertEqual(DICT.viewer_command(config), ["glow", "-s", "light"])

    def test_http_json_decodes_response(self):
        response = mock.Mock()
        response.read.return_value = json.dumps({"ok": True}).encode("utf-8")
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=False)

        with mock.patch("chiyo_cli.builtin_tools.dictionary.urllib.request.urlopen", return_value=response):
            self.assertEqual(DICT.http_json("https://example.test", 3), {"ok": True})


if __name__ == "__main__":
    unittest.main()
