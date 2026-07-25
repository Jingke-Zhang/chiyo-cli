"""Framework-backed dictionary built-in."""

import json
import os
import shlex
import shutil
import sqlite3
import subprocess
import urllib.error
import urllib.parse
import urllib.request

from chiyo_cli.paths import expand_path
from chiyo_cli.toolkit import PickOpenTool, ToolError


DICTIONARY_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/{language}/{word}"
MYMEMORY_API_URL = "https://api.mymemory.translated.net/get?q={query}&langpair={source}|{target}"
JISHO_API_URL = "https://jisho.org/api/v1/search/words?keyword={word}"
DATAMUSE_SUG_URL = "https://api.datamuse.com/sug?s={word}&max={max_results}"
DATAMUSE_WORDS_URL = "https://api.datamuse.com/words?{query}"
MYMEMORY_LANGUAGE_CODES = {
    "en": "en",
    "ja": "ja",
    "zh": "zh-CN",
}
LANGUAGE_ALIASES = {
    "jp": "ja",
    "jpn": "ja",
    "zh-cn": "zh",
    "zh-hans": "zh",
    "cn": "zh",
}

DEFAULT_CONFIG = {
    "input_language": "en",
    "output_language": "en",
    "auto_cjk_language": "zh",
    "viewer": [],
    "cache": True,
    "cache_path": "~/.cache/chiyo-cli/dictionary.sqlite3",
    "timeout": 10,
    "sources": ["personal", "cache", "online"],
    "fuzzy": True,
    "fuzzy_max": 8,
    "english_enrichment": True,
    "english_usage_max": 6,
    "zh_enrichment": True,
    "zh_definition_max": 4,
    "pronunciation": True,
    "entries": {},
}
ENGLISH_PREPOSITIONS = {
    "about",
    "above",
    "across",
    "after",
    "against",
    "among",
    "around",
    "at",
    "before",
    "behind",
    "between",
    "by",
    "for",
    "from",
    "in",
    "into",
    "of",
    "on",
    "over",
    "through",
    "to",
    "under",
    "with",
    "within",
    "without",
}
PINYIN_MAP = {
    "的": "de",
    "一": "yi",
    "是": "shi",
    "不": "bu",
    "了": "le",
    "在": "zai",
    "人": "ren",
    "有": "you",
    "我": "wo",
    "他": "ta",
    "这": "zhe",
    "中": "zhong",
    "大": "da",
    "来": "lai",
    "上": "shang",
    "国": "guo",
    "个": "ge",
    "到": "dao",
    "说": "shuo",
    "们": "men",
    "为": "wei",
    "子": "zi",
    "和": "he",
    "你": "ni",
    "地": "di",
    "出": "chu",
    "道": "dao",
    "也": "ye",
    "时": "shi",
    "年": "nian",
    "得": "de",
    "就": "jiu",
    "那": "na",
    "要": "yao",
    "下": "xia",
    "以": "yi",
    "生": "sheng",
    "会": "hui",
    "自": "zi",
    "着": "zhe",
    "去": "qu",
    "之": "zhi",
    "过": "guo",
    "家": "jia",
    "学": "xue",
    "对": "dui",
    "可": "ke",
    "她": "ta",
    "里": "li",
    "后": "hou",
    "小": "xiao",
    "么": "me",
    "心": "xin",
    "多": "duo",
    "天": "tian",
    "而": "er",
    "能": "neng",
    "好": "hao",
    "都": "dou",
    "然": "ran",
    "没": "mei",
    "日": "ri",
    "于": "yu",
    "起": "qi",
    "还": "hai",
    "发": "fa",
    "成": "cheng",
    "事": "shi",
    "只": "zhi",
    "作": "zuo",
    "当": "dang",
    "想": "xiang",
    "看": "kan",
    "文": "wen",
    "无": "wu",
    "开": "kai",
    "手": "shou",
    "十": "shi",
    "用": "yong",
    "主": "zhu",
    "行": "xing",
    "方": "fang",
    "又": "you",
    "如": "ru",
    "前": "qian",
    "所": "suo",
    "本": "ben",
    "见": "jian",
    "经": "jing",
    "验": "yan",
    "知": "zhi",
    "识": "shi",
    "认": "ren",
    "论": "lun",
    "语": "yu",
    "言": "yan",
    "词": "ci",
    "义": "yi",
    "意": "yi",
    "味": "wei",
    "翻": "fan",
    "译": "yi",
    "日": "ri",
    "英": "ying",
    "德": "de",
    "研": "yan",
    "究": "jiu",
    "问": "wen",
    "题": "ti",
    "资": "zi",
    "料": "liao",
    "项": "xiang",
    "目": "mu",
    "系": "xi",
    "统": "tong",
    "工": "gong",
    "具": "ju",
}


def normalize_word(word):
    return " ".join(str(word).split())


def normalize_language(language):
    normalized = str(language).strip().lower()
    return LANGUAGE_ALIASES.get(normalized, normalized)


def is_hiragana(char):
    return "\u3040" <= char <= "\u309f"


def is_katakana(char):
    return "\u30a0" <= char <= "\u30ff"


def is_cjk(char):
    return (
        "\u3400" <= char <= "\u4dbf"
        or "\u4e00" <= char <= "\u9fff"
        or "\uf900" <= char <= "\ufaff"
    )


def detect_language(text, auto_cjk_language="zh"):
    for char in text:
        if is_hiragana(char) or is_katakana(char):
            return "ja"

    if any(is_cjk(char) for char in text):
        return normalize_language(auto_cjk_language or "zh")

    return "en"


def contains_cjk(text):
    return any(is_cjk(char) for char in str(text))


def resolve_input_language(language, word, config):
    language = normalize_language(language)

    if language != "auto":
        return language

    return detect_language(word, config.get("auto_cjk_language", "zh"))


def cache_key(word, input_language, output_language):
    return (
        normalize_word(word).casefold(),
        normalize_language(input_language).casefold(),
        normalize_language(output_language).casefold(),
    )


def personal_entry(config, word, input_language, output_language):
    entries = config.get("entries", {})
    entry = entries.get(word) or entries.get(normalize_word(word).casefold())

    if not isinstance(entry, dict):
        return None

    language_key = f"{input_language}-{output_language}"
    value = (
        entry.get(language_key)
        or entry.get(output_language)
        or entry.get("meaning")
        or entry.get("meanings")
    )

    if value is None:
        return None

    return format_personal_entry(word, input_language, output_language, value, entry)


def format_personal_entry(word, input_language, output_language, value, entry):
    lines = [
        f"# {word}",
        "",
        f"{input_language} -> {output_language}",
        "",
    ]

    if isinstance(value, list):
        lines.extend(f"- {item}" for item in value)
    else:
        lines.append(str(value))

    note = entry.get("note")

    if note:
        lines.extend(["", "## Note", "", str(note)])

    return "\n".join(lines) + "\n"


def ensure_cache(path):
    path = expand_path(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS entries (
            word TEXT NOT NULL,
            input_language TEXT NOT NULL,
            output_language TEXT NOT NULL,
            content TEXT NOT NULL,
            PRIMARY KEY (word, input_language, output_language)
        )
        """
    )
    return connection


def read_cache(config, word, input_language, output_language):
    if not config.get("cache", True):
        return None

    path = expand_path(config["cache_path"])

    if not os.path.exists(path):
        return None

    key = cache_key(word, input_language, output_language)

    with sqlite3.connect(path) as connection:
        row = connection.execute(
            """
            SELECT content FROM entries
            WHERE word = ? AND input_language = ? AND output_language = ?
            """,
            key,
        ).fetchone()

    return None if row is None else row[0]


def write_cache(config, word, input_language, output_language, content):
    if not config.get("cache", True):
        return

    key = cache_key(word, input_language, output_language)

    with ensure_cache(config["cache_path"]) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO entries
            (word, input_language, output_language, content)
            VALUES (?, ?, ?, ?)
            """,
            (*key, content),
        )


def http_json(url, timeout):
    request = urllib.request.Request(url, headers={"User-Agent": "chiyo-cli"})

    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def http_query_url(base, params):
    return base.format(query=urllib.parse.urlencode(params))


def unique_values(values):
    seen = set()
    result = []

    for value in values:
        value = normalize_word(value)
        key = value.casefold()

        if not value or key in seen:
            continue

        seen.add(key)
        result.append(value)

    return result


def japanese_readings_from_jisho_data(data):
    entries = data.get("data", []) if isinstance(data, dict) else []
    readings = []

    for entry in entries:
        for item in entry.get("japanese", []):
            reading = item.get("reading")

            if reading:
                readings.append(reading)

    return unique_values(readings)


def lookup_japanese_readings(word, timeout):
    url = JISHO_API_URL.format(word=urllib.parse.quote(word))
    data = http_json(url, timeout)
    return japanese_readings_from_jisho_data(data)


def pinyin_with_optional_library(text):
    try:
        from pypinyin import lazy_pinyin
    except ImportError:
        return None

    return " ".join(lazy_pinyin(text))


def pinyin_with_builtin_map(text):
    syllables = []

    for char in str(text):
        if is_cjk(char):
            syllables.append(PINYIN_MAP.get(char, char))

    if not syllables or any(is_cjk(syllable) for syllable in syllables):
        return None

    return " ".join(syllables)


def chinese_pronunciation(text):
    text = normalize_word(text)

    if not contains_cjk(text):
        return None

    return pinyin_with_optional_library(text) or pinyin_with_builtin_map(text)


def pronunciation_for_text(text, language, config):
    if not config.get("pronunciation", True):
        return None

    language = normalize_language(language)

    try:
        if language == "ja":
            readings = lookup_japanese_readings(text, config.get("timeout", 10))
            return ", ".join(readings[:3]) if readings else None

        if language == "zh":
            return chinese_pronunciation(text)
    except Exception:
        return None

    return None


def append_pronunciation(lines, label, text, language, config):
    pronunciation = pronunciation_for_text(text, language, config)

    if pronunciation:
        lines.extend(["", f"{label}: {pronunciation}"])


def lookup_dictionaryapi(word, language, timeout):
    url = DICTIONARY_API_URL.format(
        language=urllib.parse.quote(language),
        word=urllib.parse.quote(word),
    )
    try:
        data = http_json(url, timeout)
    except urllib.error.HTTPError as error:
        raise ToolError(f"no definition found for {word}.") from error
    except urllib.error.URLError as error:
        raise ToolError(f"dictionary lookup failed for {word}: {error.reason}") from error

    return format_dictionaryapi(word, language, data)


def dictionaryapi_data(word, language, timeout):
    url = DICTIONARY_API_URL.format(
        language=urllib.parse.quote(language),
        word=urllib.parse.quote(word),
    )
    return http_json(url, timeout)


def format_dictionaryapi(word, language, data):
    if not data or not isinstance(data, list):
        raise ToolError(f"no definition found for {word}.")

    lines = [f"# {word}", "", f"{language} -> {language}"]
    phonetics = [
        item.get("text")
        for entry in data
        for item in entry.get("phonetics", [])
        if item.get("text")
    ]
    origins = [
        entry.get("origin")
        for entry in data
        if entry.get("origin")
    ]

    if phonetics:
        lines.extend(["", f"Pronunciation: {phonetics[0]}"])

    if origins:
        lines.extend(["", "## Etymology", "", origins[0]])

    for entry in data:
        for meaning in entry.get("meanings", []):
            part = meaning.get("partOfSpeech", "")
            definitions = meaning.get("definitions", [])
            synonyms = meaning.get("synonyms", [])
            antonyms = meaning.get("antonyms", [])

            if part:
                lines.extend(["", f"## {part}"])

            if synonyms:
                lines.append(f"Synonyms: {', '.join(synonyms[:8])}")

            if antonyms:
                lines.append(f"Antonyms: {', '.join(antonyms[:8])}")

            for index, definition in enumerate(definitions[:5], start=1):
                text = definition.get("definition")

                if not text:
                    continue

                lines.append(f"{index}. {text}")
                example = definition.get("example")

                if example:
                    lines.append(f"   Example: {example}")

                definition_synonyms = definition.get("synonyms", [])
                definition_antonyms = definition.get("antonyms", [])

                if definition_synonyms:
                    lines.append(f"   Synonyms: {', '.join(definition_synonyms[:8])}")

                if definition_antonyms:
                    lines.append(f"   Antonyms: {', '.join(definition_antonyms[:8])}")

    return "\n".join(lines).rstrip() + "\n"


def datamuse_words(params, timeout):
    return http_json(http_query_url(DATAMUSE_WORDS_URL, params), timeout)


def lookup_datamuse_suggestions(word, timeout, max_results=8):
    max_results = int(max_results or 8)
    url = DATAMUSE_SUG_URL.format(
        word=urllib.parse.quote(word),
        max_results=max_results,
    )
    suggestions = http_json(url, timeout)

    if not isinstance(suggestions, list):
        return []

    return normalize_datamuse_suggestions(suggestions, max_results)


def lookup_datamuse_spelled_like(word, timeout, max_results=8):
    data = datamuse_words(
        {
            "sp": word,
            "qe": "sp",
            "md": "dpsrf",
            "ipa": "1",
            "max": str(max_results),
        },
        timeout,
    )

    if not isinstance(data, list):
        return []

    return normalize_datamuse_suggestions(data, max_results)


def normalize_datamuse_suggestions(items, max_results):
    seen = set()
    normalized = []

    for item in items:
        if not isinstance(item, dict) or not item.get("word"):
            continue

        word = normalize_word(item["word"])
        key = word.casefold()

        if not word or key in seen:
            continue

        seen.add(key)
        normalized.append(
            {
                "word": word,
                "score": item.get("score", 0),
                "defs": item.get("defs", []),
                "tags": item.get("tags", []),
            }
        )

        if len(normalized) >= max_results:
            break

    return normalized


def fuzzy_suggestions(word, input_language, output_language, config):
    if not config.get("fuzzy", True):
        return []

    if (
        normalize_language(input_language) != "en"
        or normalize_language(output_language) != "en"
    ):
        return []

    timeout = config.get("timeout", 10)
    max_results = config.get("fuzzy_max", 8)
    suggestions = lookup_datamuse_suggestions(word, timeout, max_results)

    if suggestions:
        return suggestions

    return lookup_datamuse_spelled_like(word, timeout, max_results)


def datamuse_exact_metadata(word, timeout):
    data = datamuse_words(
        {
            "sp": word,
            "qe": "sp",
            "md": "dpsrf",
            "ipa": "1",
            "max": "1",
        },
        timeout,
    )

    if not isinstance(data, list):
        return None

    for item in data:
        if item.get("word", "").casefold() == word.casefold():
            return item

    return data[0] if data else None


def datamuse_related_words(word, relation, timeout, max_results):
    data = datamuse_words(
        {
            f"rel_{relation}": word,
            "max": str(max_results),
        },
        timeout,
    )

    if not isinstance(data, list):
        return []

    return [
        normalize_word(item["word"])
        for item in data
        if isinstance(item, dict) and item.get("word")
    ]


def format_word_list(words):
    return ", ".join(words)


def append_english_enrichment(content, word, config):
    if not config.get("english_enrichment", True):
        return content

    timeout = config.get("timeout", 10)
    usage_max = int(config.get("english_usage_max", 6) or 6)
    lines = [content.rstrip()]

    try:
        metadata = datamuse_exact_metadata(word, timeout)
    except Exception:
        metadata = None

    if metadata:
        details = []
        headword = metadata.get("defHeadword")
        syllables = metadata.get("numSyllables")
        tags = metadata.get("tags", [])
        pronunciation = next(
            (tag.removeprefix("pron:") for tag in tags if tag.startswith("pron:")),
            None,
        )
        frequency = next(
            (tag.removeprefix("f:") for tag in tags if tag.startswith("f:")),
            None,
        )

        if headword and headword.casefold() != word.casefold():
            details.append(f"Base form: {headword}")

        if syllables:
            details.append(f"Syllables: {syllables}")

        if pronunciation and "Pronunciation:" not in content:
            details.append(f"Pronunciation: {pronunciation}")

        if frequency:
            details.append(f"Frequency: {frequency} per million words")

        if details:
            lines.extend(["", "## Word Form", "", *details])

    try:
        followers = datamuse_related_words(word, "bga", timeout, usage_max * 2)
        predecessors = datamuse_related_words(word, "bgb", timeout, usage_max)
        triggered = datamuse_related_words(word, "trg", timeout, usage_max)
    except Exception:
        followers = []
        predecessors = []
        triggered = []

    prepositions = [
        candidate
        for candidate in followers
        if candidate.casefold() in ENGLISH_PREPOSITIONS
    ][:usage_max]

    if prepositions or followers or predecessors or triggered:
        lines.extend(["", "## Usage"])

        if prepositions:
            lines.extend(["", f"Preposition patterns: {format_word_list(prepositions)}"])

        if followers:
            lines.extend(["", f"Frequent followers: {format_word_list(followers[:usage_max])}"])

        if predecessors:
            lines.extend(["", f"Frequent predecessors: {format_word_list(predecessors[:usage_max])}"])

        if triggered:
            lines.extend(["", f"Associated words: {format_word_list(triggered[:usage_max])}"])

    return "\n".join(lines).rstrip() + "\n"


def lookup_jisho(word, timeout):
    url = JISHO_API_URL.format(word=urllib.parse.quote(word))
    data = http_json(url, timeout)
    return format_jisho(word, data)


def format_jisho(word, data):
    entries = data.get("data", []) if isinstance(data, dict) else []

    if not entries:
        raise ToolError(f"no Japanese definition found for {word}.")

    lines = [f"# {word}", "", "ja -> ja"]
    readings = japanese_readings_from_jisho_data(data)

    if readings:
        lines.extend(["", f"Pronunciation: {', '.join(readings[:3])}"])

    for entry in entries[:5]:
        japanese = entry.get("japanese", [])
        readings = []

        for item in japanese:
            word_text = item.get("word")
            reading = item.get("reading")

            if word_text and reading and word_text != reading:
                readings.append(f"{word_text} [{reading}]")
            elif word_text or reading:
                readings.append(word_text or reading)

        if readings:
            lines.extend(["", "## " + "; ".join(readings)])

        for sense in entry.get("senses", []):
            parts = ", ".join(sense.get("parts_of_speech", []))
            meanings = "; ".join(sense.get("english_definitions", []))

            if not meanings:
                continue

            if parts:
                lines.append(f"- ({parts}) {meanings}")
            else:
                lines.append(f"- {meanings}")

    return "\n".join(lines).rstrip() + "\n"


def mymemory_language(language):
    language = normalize_language(language)
    return MYMEMORY_LANGUAGE_CODES.get(language, language)


def mymemory_url(text, input_language, output_language):
    source = mymemory_language(input_language)
    target = mymemory_language(output_language)
    return MYMEMORY_API_URL.format(
        query=urllib.parse.quote(text),
        source=urllib.parse.quote(source),
        target=urllib.parse.quote(target),
    )


def lookup_mymemory_data(text, input_language, output_language, timeout):
    return http_json(mymemory_url(text, input_language, output_language), timeout)


def mymemory_translated_text(data, word):
    translated = data.get("responseData", {}).get("translatedText")

    if not translated:
        raise ToolError(f"no translation found for {word}.")

    return normalize_word(translated)


def mymemory_matches(data, primary=None):
    matches = data.get("matches", [])

    if not isinstance(matches, list):
        return []

    seen = set()
    normalized = []

    for match in matches:
        if not isinstance(match, dict) or not match.get("translation"):
            continue

        translation = normalize_word(match["translation"])
        key = translation.casefold()

        if not translation or key in seen or translation == primary:
            continue

        seen.add(key)
        normalized.append(
            {
                "translation": translation,
                "quality": match.get("quality"),
                "match": match.get("match"),
            }
        )

    return normalized


def translate_text(text, input_language, output_language, timeout):
    data = lookup_mymemory_data(text, input_language, output_language, timeout)
    return mymemory_translated_text(data, text)


def dictionaryapi_definition_rows(data, max_results):
    rows = []

    if not isinstance(data, list):
        return rows

    for entry in data:
        for meaning in entry.get("meanings", []):
            part = meaning.get("partOfSpeech", "")

            for definition in meaning.get("definitions", []):
                text = definition.get("definition")

                if not text:
                    continue

                rows.append(
                    {
                        "part": part,
                        "definition": text,
                        "example": definition.get("example", ""),
                    }
                )

                if len(rows) >= max_results:
                    return rows

    return rows


def append_translation_alternatives(lines, data, primary, limit=6):
    alternatives = mymemory_matches(data, primary=primary)[:limit]

    if not alternatives:
        return

    lines.extend(["", "## Alternatives"])

    for item in alternatives:
        details = []

        if item.get("quality") not in (None, ""):
            details.append(f"quality {item['quality']}")

        if item.get("match") not in (None, ""):
            details.append(f"match {item['match']}")

        suffix = f" ({', '.join(details)})" if details else ""
        lines.append(f"- {item['translation']}{suffix}")


def append_zh_definition_enrichment(lines, word, input_language, timeout, config):
    if not config.get("zh_enrichment", True):
        return

    if normalize_language(input_language) != "en":
        return

    max_results = int(config.get("zh_definition_max", 4) or 4)

    try:
        data = dictionaryapi_data(word, "en", timeout)
    except Exception:
        return

    rows = dictionaryapi_definition_rows(data, max_results)

    if not rows:
        return

    lines.extend(["", "## Definitions"])

    for index, row in enumerate(rows, start=1):
        try:
            translated_definition = translate_text(
                row["definition"],
                "en",
                "zh",
                timeout,
            )
        except Exception:
            translated_definition = ""

        label = f"{index}."

        if row["part"]:
            label = f"{index}. ({row['part']})"

        if translated_definition:
            lines.append(f"{label} {translated_definition}")
            lines.append(f"   Source: {row['definition']}")
        else:
            lines.append(f"{label} {row['definition']}")

        if row["example"]:
            try:
                translated_example = translate_text(row["example"], "en", "zh", timeout)
            except Exception:
                translated_example = ""

            if translated_example:
                lines.append(f"   Example: {translated_example}")

            lines.append(f"   Source example: {row['example']}")


def format_mymemory(word, input_language, output_language, data, timeout, config):
    translated = mymemory_translated_text(data, word)
    pronunciation_config = dict(config)
    pronunciation_config.setdefault("timeout", timeout)
    lines = [
        f"# {word}",
        "",
        f"{input_language} -> {output_language}",
    ]
    append_pronunciation(
        lines,
        "Input pronunciation",
        word,
        input_language,
        pronunciation_config,
    )
    lines.extend(["", translated])
    append_pronunciation(
        lines,
        "Output pronunciation",
        translated,
        output_language,
        pronunciation_config,
    )

    if normalize_language(output_language) == "zh":
        append_translation_alternatives(lines, data, translated)
        append_zh_definition_enrichment(
            lines,
            word,
            input_language,
            timeout,
            pronunciation_config,
        )

    return "\n".join(lines).rstrip() + "\n"


def lookup_mymemory(word, input_language, output_language, timeout, config=None):
    config = {} if config is None else config
    data = lookup_mymemory_data(word, input_language, output_language, timeout)
    return format_mymemory(
        word,
        input_language,
        output_language,
        data,
        timeout,
        config,
    )


def lookup_online(word, input_language, output_language, timeout, config=None):
    input_language = normalize_language(input_language)
    output_language = normalize_language(output_language)
    config = {} if config is None else config

    if input_language == output_language:
        if input_language == "ja":
            return lookup_jisho(word, timeout)

        content = lookup_dictionaryapi(word, input_language, timeout)

        if input_language == "en":
            content = append_english_enrichment(content, word, config)

        return content

    return lookup_mymemory(
        word,
        input_language,
        output_language,
        timeout,
        config=config,
    )


def lookup(word, input_language, output_language, config):
    word = normalize_word(word)
    input_language = normalize_language(input_language)
    output_language = normalize_language(output_language)
    sources = config.get("sources", ["personal", "cache", "online"])

    for source in sources:
        if source == "personal":
            content = personal_entry(config, word, input_language, output_language)
        elif source == "cache":
            content = read_cache(config, word, input_language, output_language)
        elif source == "online":
            content = lookup_online(
                word,
                input_language,
                output_language,
                config.get("timeout", 10),
                config=config,
            )
            write_cache(config, word, input_language, output_language, content)
        else:
            raise ToolError(f"unknown dictionary source: {source}")

        if content:
            return content

    raise ToolError(f"no dictionary entry found for {word}.")


def viewer_command(config):
    configured = config.get("viewer", [])

    if isinstance(configured, str):
        configured = shlex.split(configured)

    if configured:
        return [str(part) for part in configured]

    pager = os.environ.get("PAGER")

    if pager:
        return shlex.split(pager)

    if shutil.which("less"):
        return ["less", "-R"]

    return ["cat"]


def render_content(content, config, execute_viewer=True):
    command = viewer_command(config)

    if not execute_viewer:
        print(content, end="")
        return content

    try:
        result = subprocess.run(
            command,
            input=content,
            text=True,
            check=False,
        )
    except FileNotFoundError as error:
        raise ToolError(f"viewer not found: {command[0]}") from error

    if result.returncode != 0:
        raise ToolError(
            f"viewer failed with exit code {result.returncode}: {' '.join(command)}"
        )

    return content


class Tool(PickOpenTool):
    name = "Dictionary"
    cmd = "def"
    author = "Chiyo CLI"
    author_id = "shiori-route"
    description = "Look up definitions or translations."
    docs = """
    # def

    Look up a word or phrase, cache the result, and show it through a pager.
    Use `-i` and `-o` to select input and output languages.
    """
    default_config = DEFAULT_CONFIG

    def add_arguments(self, parser):
        parser.add_argument(
            "-i",
            "--in",
            dest="input_language",
            default=None,
            help="Input language code. Defaults to configured input_language.",
        )
        parser.add_argument(
            "-o",
            "--out",
            dest="output_language",
            default=None,
            help="Output language code. Defaults to configured output_language.",
        )
        parser.add_argument(
            "--no-fuzzy",
            action="store_true",
            help="Disable fuzzy suggestions when an English lookup misses.",
        )

    def suggestion_display_fields(self, item, config):
        definition = ""
        defs = item.get("defs", [])

        if defs:
            definition = defs[0].split("\t", 1)[-1]

        return [
            self.primary(item["word"]),
            self.secondary(str(item.get("score", ""))),
            self.plain(definition),
        ]

    def select_suggestion(self, suggestions, args, config):
        if len(suggestions) == 1 and not args.confirm:
            return suggestions[0]

        from chiyo_cli.fzf import choose_item_from

        return choose_item_from(
            suggestions,
            config.get("fuzzy_prompt", "def fuzzy> "),
            "a dictionary suggestion",
            self.fail,
            display_fields=lambda item: self.suggestion_display_fields(item, config),
            search_display_fields=[1, 3],
        )

    def run(self, argv=None, config=None, execute_shell_actions=True):
        config = dict(self.default_config if config is None else config)
        args = self.parser().parse_args(argv)

        if args.list_completions:
            return None

        word = normalize_word(" ".join(args.query))

        if not word:
            self.fail("word is required.")

        input_language = resolve_input_language(
            args.input_language or config.get("input_language", "en"),
            word,
            config,
        )
        output_language = normalize_language(
            args.output_language or config.get("output_language", "en")
        )

        try:
            content = lookup(word, input_language, output_language, config)
        except ToolError as error:
            if args.no_fuzzy:
                self.fail(str(error))

            try:
                suggestions = fuzzy_suggestions(
                    word,
                    input_language,
                    output_language,
                    config,
                )
            except Exception:
                suggestions = []

            if not suggestions:
                self.fail(str(error))

            selected = self.select_suggestion(suggestions, args, config)

            if selected is None:
                return None

            try:
                content = lookup(
                    selected["word"],
                    input_language,
                    output_language,
                    config,
                )
            except ToolError as retry_error:
                self.fail(str(retry_error))

        return render_content(
            content,
            config,
            execute_viewer=execute_shell_actions,
        )

    def items(self, config):
        return []

    def display_fields(self, item, config):
        return []

    def open_item(self, item, args, config):
        return None
