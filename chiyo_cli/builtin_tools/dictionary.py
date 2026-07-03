"""Framework-backed dictionary built-in."""

import json
import os
import shlex
import shutil
import sqlite3
import subprocess
import urllib.parse
import urllib.request

from chiyo_cli.paths import expand_path
from chiyo_cli.toolkit import PickOpenTool, ToolError


DICTIONARY_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/{language}/{word}"
MYMEMORY_API_URL = "https://api.mymemory.translated.net/get?q={query}&langpair={source}|{target}"
JISHO_API_URL = "https://jisho.org/api/v1/search/words?keyword={word}"
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
    "viewer": [],
    "cache": True,
    "cache_path": "~/.cache/chiyo-cli/dictionary.sqlite3",
    "timeout": 10,
    "sources": ["personal", "cache", "online"],
    "entries": {},
}


def normalize_word(word):
    return " ".join(str(word).split())


def normalize_language(language):
    normalized = str(language).strip().lower()
    return LANGUAGE_ALIASES.get(normalized, normalized)


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


def lookup_dictionaryapi(word, language, timeout):
    url = DICTIONARY_API_URL.format(
        language=urllib.parse.quote(language),
        word=urllib.parse.quote(word),
    )
    data = http_json(url, timeout)
    return format_dictionaryapi(word, language, data)


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

    if phonetics:
        lines.extend(["", f"Pronunciation: {phonetics[0]}"])

    for entry in data:
        for meaning in entry.get("meanings", []):
            part = meaning.get("partOfSpeech", "")
            definitions = meaning.get("definitions", [])

            if part:
                lines.extend(["", f"## {part}"])

            for index, definition in enumerate(definitions[:5], start=1):
                text = definition.get("definition")

                if not text:
                    continue

                lines.append(f"{index}. {text}")
                example = definition.get("example")

                if example:
                    lines.append(f"   Example: {example}")

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


def lookup_mymemory(word, input_language, output_language, timeout):
    source = mymemory_language(input_language)
    target = mymemory_language(output_language)
    url = MYMEMORY_API_URL.format(
        query=urllib.parse.quote(word),
        source=urllib.parse.quote(source),
        target=urllib.parse.quote(target),
    )
    data = http_json(url, timeout)
    translated = data.get("responseData", {}).get("translatedText")

    if not translated:
        raise ToolError(f"no translation found for {word}.")

    return "\n".join(
        [
            f"# {word}",
            "",
            f"{input_language} -> {output_language}",
            "",
            translated,
            "",
        ]
    )


def lookup_online(word, input_language, output_language, timeout):
    input_language = normalize_language(input_language)
    output_language = normalize_language(output_language)

    if input_language == output_language:
        if input_language == "ja":
            return lookup_jisho(word, timeout)

        return lookup_dictionaryapi(word, input_language, timeout)

    return lookup_mymemory(word, input_language, output_language, timeout)


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
    author_id = "Jingke-Zhang"
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

    def run(self, argv=None, config=None, execute_shell_actions=True):
        config = dict(self.default_config if config is None else config)
        args = self.parser().parse_args(argv)

        if args.list_completions:
            return None

        word = normalize_word(" ".join(args.query))

        if not word:
            self.fail("word is required.")

        input_language = normalize_language(
            args.input_language or config.get("input_language", "en")
        )
        output_language = normalize_language(
            args.output_language or config.get("output_language", "en")
        )

        try:
            content = lookup(word, input_language, output_language, config)
            return render_content(
                content,
                config,
                execute_viewer=execute_shell_actions,
            )
        except ToolError as error:
            self.fail(str(error))

    def items(self, config):
        return []

    def display_fields(self, item, config):
        return []

    def open_item(self, item, args, config):
        return None
