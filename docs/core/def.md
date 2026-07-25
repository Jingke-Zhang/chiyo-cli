# def

Look up a word or phrase from the terminal and show the result through a pager.

```sh
chiyo run def epistemic
chiyo run def -i en -o zh epistemic
chiyo run def -i ja -o zh 言葉
chiyo run def -i zh -o ja 知识
chiyo run def -i auto -o en ことば
chiyo run def empircal
chiyo install def
def empirical
```

By default `def` treats input and output as English (`-i en -o en`) and returns
English definitions. When the languages differ, it asks an online translation
source for a translation instead:

```sh
def -i en -o zh "bounded rationality"
def -i ja -o en 言葉
def -i en -o ja knowledge
def -i zh -o ja 知识
def -i auto -o zh epistemic
```

Use `-i auto` to infer the input language. Kana is treated as Japanese, CJK
characters without kana use `auto_cjk_language`, and Latin text defaults to
English. Pure CJK words can be ambiguous between Chinese and Japanese, so the
default is configurable.

When an English definition lookup misses, `def` can ask for fuzzy suggestions,
show the candidates in `fzf`, and then look up the selected word. Use
`--no-fuzzy` to keep strict exact-match behavior for a single lookup.

## Sources

`def` checks sources in this order by default:

1. `personal`: configured personal glossary entries
2. `cache`: previous online results stored in SQLite
3. `online`: dictionary or translation provider

For same-language lookup, the online provider uses dictionaryapi.dev for
English and Jisho for Japanese. English definitions also include any available
etymology, synonyms, antonyms, word-form metadata, frequent followers and
predecessors, associated words, and simple preposition patterns. The extra
English metadata and fuzzy candidates come from Datamuse.

For different input/output languages, `def` uses MyMemory translation. The
CLI-facing language codes `ja`, `zh`, and `en` can be used in any direction;
internally `zh` is sent to MyMemory as `zh-CN`.

When the output language is Chinese, `def` also shows alternative translations
from MyMemory. For English-to-Chinese lookups, it enriches the result with a
small number of English dictionary definitions translated into Chinese, while
keeping the original English source lines below them.

Japanese and Chinese text include pronunciation when possible. Japanese
readings come from Jisho. Chinese pinyin uses the optional `pypinyin` package
when it is installed, with a small built-in common-character map as a fallback.

## Config

Default generated config:

```toml
["shiori-route/dictionary"]
cmds = ["def"]
input_language = "en"
output_language = "en"
auto_cjk_language = "zh"
viewer = []
cache = true
cache_path = "~/.cache/chiyo-cli/dictionary.sqlite3"
timeout = 10
sources = ["personal", "cache", "online"]
fuzzy = true
fuzzy_max = 8
english_enrichment = true
english_usage_max = 6
zh_enrichment = true
zh_definition_max = 4
pronunciation = true
```

Set `input_language = "auto"` to make automatic input language detection the
default, and set `auto_cjk_language = "ja"` if pure CJK words should be treated
as Japanese by default.

`viewer = []` means Chiyo chooses `$PAGER`, then `less -R`, then `cat`. Set it
explicitly to use another viewer:

```toml
["shiori-route/dictionary"]
viewer = ["bat", "--language", "markdown", "--paging", "always"]
```

String commands are also split like shell words:

```toml
["shiori-route/dictionary"]
viewer = "glow -s light"
```

Shell aliases are not expanded here because Chiyo runs the viewer directly
without an interactive shell. Use a string command, an argument list, or set
`PAGER = "glow -s light"` in the environment instead of relying on
`alias glow="glow -s light"`.

Personal entries live under `entries`. A generic `meaning` works for every
language pair, while `en-zh` or `zh` can override a specific output:

```toml
["shiori-route/dictionary".entries.epistemic]
meaning = "relating to knowledge or knowing"
en-zh = "认识论的；知识相关的"
note = "Common in epistemic uncertainty."
```

Disable online lookup by removing `online` from `sources`:

```toml
["shiori-route/dictionary"]
sources = ["personal", "cache"]
```

Disable fuzzy lookup or English enrichment separately:

```toml
["shiori-route/dictionary"]
fuzzy = false
english_enrichment = false
zh_enrichment = false
```

Disable Japanese and Chinese pronunciation lines:

```toml
["shiori-route/dictionary"]
pronunciation = false
```
