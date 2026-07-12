# s

`s` opens web search URLs from the terminal. It maps short engine keys to URL
templates, URL-encodes the query, and opens the generated URL in the system
default browser.

```sh
chiyo run s g wavelet tree
chiyo run s gh chiyo-cli
chiyo run s scholar beaver triple
chiyo run s wavelet tree
chiyo run s -- g wavelet tree
chiyo doc s
chiyo config init s --append
chiyo run s --list-completions
chiyo install s
```

## Options

- `--list-completions`: print configured engine keys for shell completion

## Config

Default generated config:

```toml
["shiori-route/web-search"]
cmds = ["s"]
fzf_prompt = "s> "

["shiori-route/web-search".engines.g]
name = "Google"
url = "https://www.google.com/search?q={query}"

["shiori-route/web-search".engines.gh]
name = "GitHub"
url = "https://github.com/search?q={query}"

["shiori-route/web-search".engines.ytb]
name = "YouTube"
url = "https://www.youtube.com/results?search_query={query}"

["shiori-route/web-search".engines.scholar]
name = "Google Scholar"
url = "https://scholar.google.com/scholar?q={query}"
```

When the first argument is a configured engine key, `s` uses that engine
directly. Otherwise it opens `fzf` to choose an engine. Use `--` when the query
itself starts with an engine key.

When `["shiori-route/web-search"]` is present in the config file, configured engines are
treated as the complete engine set. Delete an engine table to disable that key.

## Completion Data

`chiyo run s --list-completions` prints one configured engine key per line.
User-added engines under `["shiori-route/web-search".engines.*]` appear automatically.

## Framework Entry

`s` is a framework-backed built-in tool. `chiyo run s ...` reads `["shiori-route/web-search"]` from
`tools.toml`; `chiyo install s` creates an optional direct wrapper and
completion.
