# def

Look up a word or phrase from the terminal and show the result through a pager.

```sh
chiyo run def epistemic
chiyo run def -i en -o zh epistemic
chiyo run def -i ja -o zh 言葉
chiyo run def -i zh -o ja 知识
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
```

## Sources

`def` checks sources in this order by default:

1. `personal`: configured personal glossary entries
2. `cache`: previous online results stored in SQLite
3. `online`: dictionary or translation provider

For same-language lookup, the online provider uses dictionaryapi.dev for
English and Jisho for Japanese. For different input/output languages, it uses
MyMemory translation. The CLI-facing language codes `ja`, `zh`, and `en` can be
used in any direction; internally `zh` is sent to MyMemory as `zh-CN`.

## Config

Default generated config:

```toml
["jingke-zhang/dictionary"]
cmds = ["def"]
input_language = "en"
output_language = "en"
viewer = []
cache = true
cache_path = "~/.cache/chiyo-cli/dictionary.sqlite3"
timeout = 10
sources = ["personal", "cache", "online"]
```

`viewer = []` means Chiyo chooses `$PAGER`, then `less -R`, then `cat`. Set it
explicitly to use another viewer:

```toml
["jingke-zhang/dictionary"]
viewer = ["bat", "--language", "markdown", "--paging", "always"]
```

String commands are also split like shell words:

```toml
["jingke-zhang/dictionary"]
viewer = "glow -s light"
```

Shell aliases are not expanded here because Chiyo runs the viewer directly
without an interactive shell. Use a string command, an argument list, or set
`PAGER = "glow -s light"` in the environment instead of relying on
`alias glow="glow -s light"`.

Personal entries live under `entries`. A generic `meaning` works for every
language pair, while `en-zh` or `zh` can override a specific output:

```toml
["jingke-zhang/dictionary".entries.epistemic]
meaning = "relating to knowledge or knowing"
en-zh = "认识论的；知识相关的"
note = "Common in epistemic uncertainty."
```

Disable online lookup by removing `online` from `sources`:

```toml
["jingke-zhang/dictionary"]
sources = ["personal", "cache"]
```
