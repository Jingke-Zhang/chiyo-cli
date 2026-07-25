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

    def test_format_dictionaryapi_renders_rich_english_fields(self):
        content = DICT.format_dictionaryapi(
            "test",
            "en",
            [
                {
                    "origin": "late Middle English",
                    "meanings": [
                        {
                            "partOfSpeech": "verb",
                            "synonyms": ["examine"],
                            "antonyms": ["ignore"],
                            "definitions": [
                                {
                                    "definition": "Take measures to check quality.",
                                    "synonyms": ["check"],
                                    "antonyms": ["neglect"],
                                }
                            ],
                        }
                    ],
                }
            ],
        )

        self.assertIn("## Etymology", content)
        self.assertIn("late Middle English", content)
        self.assertIn("Synonyms: examine", content)
        self.assertIn("Antonyms: ignore", content)
        self.assertIn("Synonyms: check", content)
        self.assertIn("Antonyms: neglect", content)

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
        self.assertIn("Pronunciation: ことば", content)
        self.assertIn("## 言葉 [ことば]", content)
        self.assertIn("- (Noun) word; language", content)

    def test_detect_language_identifies_kana_as_japanese(self):
        self.assertEqual(DICT.detect_language("ことば"), "ja")
        self.assertEqual(DICT.detect_language("カタカナ"), "ja")
        self.assertEqual(DICT.detect_language("食べる"), "ja")

    def test_detect_language_uses_configured_cjk_default(self):
        self.assertEqual(DICT.detect_language("知识"), "zh")
        self.assertEqual(DICT.detect_language("言葉", auto_cjk_language="ja"), "ja")

    def test_detect_language_defaults_latin_to_english(self):
        self.assertEqual(DICT.detect_language("epistemic"), "en")

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

        content = DICT.lookup_online(
            "empirical",
            "en",
            "en",
            5,
            config={"english_enrichment": False},
        )

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

        content = DICT.lookup_online(
            "empirical",
            "en",
            "zh",
            5,
            config={"pronunciation": False, "zh_enrichment": False},
        )

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
                DICT.lookup_online(
                    "term",
                    input_language,
                    output_language,
                    5,
                    config={"pronunciation": False, "zh_enrichment": False},
                )
                self.assertIn(expected_url, http_json.call_args.args[0])

    @mock.patch("chiyo_cli.builtin_tools.dictionary.http_json")
    def test_lookup_online_accepts_language_aliases(self, http_json):
        http_json.return_value = {
            "responseData": {
                "translatedText": "translated",
            }
        }

        DICT.lookup_online(
            "term",
            "jp",
            "zh-cn",
            5,
            config={"pronunciation": False, "zh_enrichment": False},
        )

        self.assertIn("langpair=ja|zh-CN", http_json.call_args.args[0])

    def test_format_mymemory_adds_chinese_alternatives(self):
        content = DICT.format_mymemory(
            "knowledge",
            "en",
            "zh",
            {
                "responseData": {"translatedText": "知识"},
                "matches": [
                    {"translation": "知识", "quality": "100", "match": 1},
                    {"translation": "认识", "quality": "80", "match": 0.8},
                ],
            },
            5,
            {"pronunciation": False, "zh_enrichment": False},
        )

        self.assertIn("知识", content)
        self.assertIn("## Alternatives", content)
        self.assertIn("- 认识 (quality 80, match 0.8)", content)

    @mock.patch("chiyo_cli.builtin_tools.dictionary.translate_text")
    @mock.patch("chiyo_cli.builtin_tools.dictionary.dictionaryapi_data")
    def test_chinese_output_enrichment_adds_translated_english_definitions(
        self,
        dictionaryapi_data,
        translate_text,
    ):
        dictionaryapi_data.return_value = [
            {
                "meanings": [
                    {
                        "partOfSpeech": "noun",
                        "definitions": [
                            {
                                "definition": "Facts, information, and skills.",
                                "example": "Knowledge is power.",
                            }
                        ],
                    }
                ]
            }
        ]
        translate_text.side_effect = ["事实、信息和技能。", "知识就是力量。"]
        lines = []

        DICT.append_zh_definition_enrichment(
            lines,
            "knowledge",
            "en",
            5,
            DICT.DEFAULT_CONFIG,
        )

        content = "\n".join(lines)
        self.assertIn("## Definitions", content)
        self.assertIn("1. (noun) 事实、信息和技能。", content)
        self.assertIn("Source: Facts, information, and skills.", content)
        self.assertIn("Example: 知识就是力量。", content)
        self.assertIn("Source example: Knowledge is power.", content)

    def test_chinese_pronunciation_uses_builtin_map(self):
        self.assertEqual(DICT.chinese_pronunciation("知识"), "zhi shi")
        self.assertEqual(DICT.chinese_pronunciation("经验的"), "jing yan de")

    @mock.patch("chiyo_cli.builtin_tools.dictionary.lookup_japanese_readings")
    @mock.patch("chiyo_cli.builtin_tools.dictionary.http_json")
    def test_translation_adds_japanese_output_pronunciation(self, http_json, readings):
        http_json.return_value = {
            "responseData": {
                "translatedText": "言葉",
            }
        }
        readings.return_value = ["ことば"]

        content = DICT.lookup_online("word", "en", "ja", 5)

        self.assertIn("word", content)
        self.assertIn("Output pronunciation: ことば", content)
        readings.assert_called_once_with("言葉", 5)

    @mock.patch("chiyo_cli.builtin_tools.dictionary.http_json")
    def test_translation_adds_chinese_output_pronunciation(self, http_json):
        http_json.return_value = {
            "responseData": {
                "translatedText": "知识",
            }
        }

        content = DICT.lookup_online("knowledge", "en", "zh", 5)

        self.assertIn("知识", content)
        self.assertIn("Output pronunciation: zhi shi", content)

    @mock.patch("chiyo_cli.builtin_tools.dictionary.datamuse_words")
    def test_append_english_enrichment_adds_word_form_and_usage(self, datamuse_words):
        datamuse_words.side_effect = [
            [
                {
                    "word": "tested",
                    "defHeadword": "test",
                    "numSyllables": 2,
                    "tags": ["pron:t ɛ s t ɪ d", "f:12.3"],
                }
            ],
            [{"word": "with"}, {"word": "against"}, {"word": "quality"}],
            [{"word": "unit"}],
            [{"word": "experiment"}],
        ]

        content = DICT.append_english_enrichment(
            "# tested\n\nbody\n",
            "tested",
            DICT.DEFAULT_CONFIG,
        )

        self.assertIn("Base form: test", content)
        self.assertIn("Syllables: 2", content)
        self.assertIn("Frequency: 12.3 per million words", content)
        self.assertIn("Preposition patterns: with, against", content)
        self.assertIn("Frequent followers: with, against, quality", content)
        self.assertIn("Frequent predecessors: unit", content)
        self.assertIn("Associated words: experiment", content)

    @mock.patch("chiyo_cli.builtin_tools.dictionary.http_json")
    def test_fuzzy_suggestions_use_datamuse_suggest(self, http_json):
        http_json.return_value = [
            {"word": "empirical", "score": 100, "defs": ["adj\tempirical"]},
            {"word": "empiric", "score": 80},
        ]

        suggestions = DICT.fuzzy_suggestions(
            "empircal",
            "en",
            "en",
            DICT.DEFAULT_CONFIG,
        )

        self.assertEqual(["empirical", "empiric"], [item["word"] for item in suggestions])
        self.assertIn("api.datamuse.com/sug", http_json.call_args.args[0])

    def test_fuzzy_suggestions_only_run_for_english_definition_lookup(self):
        self.assertEqual(
            DICT.fuzzy_suggestions("言葉", "ja", "en", DICT.DEFAULT_CONFIG),
            [],
        )

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

    @mock.patch("chiyo_cli.builtin_tools.dictionary.lookup")
    def test_run_can_auto_detect_input_language(self, lookup):
        lookup.return_value = "# 言葉\n\nword\n"

        with mock.patch("sys.stdout", new_callable=StringIO):
            DICT.Tool().run(
                ["-i", "auto", "-o", "en", "ことば"],
                config=DICT.DEFAULT_CONFIG,
                execute_shell_actions=False,
            )

        self.assertEqual(lookup.call_args.args[:3], ("ことば", "ja", "en"))

    @mock.patch("chiyo_cli.builtin_tools.dictionary.lookup")
    def test_run_auto_detect_uses_configured_cjk_default(self, lookup):
        lookup.return_value = "# 言葉\n\nword\n"
        config = dict(DICT.DEFAULT_CONFIG)
        config["input_language"] = "auto"
        config["auto_cjk_language"] = "ja"

        with mock.patch("sys.stdout", new_callable=StringIO):
            DICT.Tool().run(
                ["-o", "en", "言葉"],
                config=config,
                execute_shell_actions=False,
            )

        self.assertEqual(lookup.call_args.args[:3], ("言葉", "ja", "en"))

    @mock.patch("chiyo_cli.builtin_tools.dictionary.fuzzy_suggestions")
    @mock.patch("chiyo_cli.builtin_tools.dictionary.lookup")
    def test_run_uses_single_fuzzy_suggestion_after_lookup_miss(self, lookup, suggestions):
        lookup.side_effect = [
            DICT.ToolError("no definition found for empircal."),
            "# empirical\n\nKnown by experience.\n",
        ]
        suggestions.return_value = [{"word": "empirical", "score": 100, "defs": []}]

        with mock.patch("sys.stdout", new_callable=StringIO) as stdout:
            result = DICT.Tool().run(
                ["empircal"],
                config=DICT.DEFAULT_CONFIG,
                execute_shell_actions=False,
            )

        self.assertEqual(result, "# empirical\n\nKnown by experience.\n")
        self.assertEqual(stdout.getvalue(), "# empirical\n\nKnown by experience.\n")
        self.assertEqual(lookup.call_args_list[1].args[:3], ("empirical", "en", "en"))

    @mock.patch("chiyo_cli.builtin_tools.dictionary.fuzzy_suggestions")
    @mock.patch("chiyo_cli.builtin_tools.dictionary.lookup")
    def test_run_no_fuzzy_reports_original_lookup_miss(self, lookup, suggestions):
        lookup.side_effect = DICT.ToolError("no definition found for empircal.")

        with self.assertRaises(SystemExit):
            DICT.Tool().run(
                ["--no-fuzzy", "empircal"],
                config=DICT.DEFAULT_CONFIG,
                execute_shell_actions=False,
            )

        suggestions.assert_not_called()

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
