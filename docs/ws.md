# ws

`ws` opens web search URLs from the terminal. It maps short engine keys to URL
templates, URL-encodes the query, and opens the generated URL in the system
default browser.

```sh
chiyo run ws g wavelet tree
chiyo run ws gh chiyo-cli
chiyo run ws scholar beaver triple
chiyo run ws wavelet tree
chiyo run ws -- g wavelet tree
chiyo doc ws
chiyo config init ws --append
chiyo run ws --list-completions
chiyo install ws
```

## Options

- `--list-completions`: print configured engine keys for shell completion

## Config

Default generated config:

```toml
["chiyo/ws"]
cmds = ["ws"]
fzf_prompt = "ws> "

["chiyo/ws".engines.g]
name = "Google"
url = "https://www.google.com/search?q={query}"

["chiyo/ws".engines.gh]
name = "GitHub"
url = "https://github.com/search?q={query}"

["chiyo/ws".engines.ytb]
name = "YouTube"
url = "https://www.youtube.com/results?search_query={query}"

["chiyo/ws".engines.scholar]
name = "Google Scholar"
url = "https://scholar.google.com/scholar?q={query}"
```

When the first argument is a configured engine key, `ws` uses that engine
directly. Otherwise it opens `fzf` to choose an engine. Use `--` when the query
itself starts with an engine key.

When `["chiyo/ws"]` is present in the config file, configured engines are
treated as the complete engine set. Delete an engine table to disable that key.

## Completion Data

`chiyo run ws --list-completions` prints one configured engine key per line.
User-added engines under `["chiyo/ws".engines.*]` appear automatically.

## Framework Entry

`ws` is a framework-backed built-in tool. `chiyo run ws ...` reads `["chiyo/ws"]` from
`tools.toml`; `chiyo install ws` creates an optional direct wrapper and
completion.
