# ws

`ws` opens web search URLs from the terminal. It maps short engine keys to URL
templates, URL-encodes the query, and opens the generated URL in the system
default browser.

```sh
ws g wavelet tree
ws gh chiyo-cli
ws scholar beaver triple
ws wavelet tree
ws -- g wavelet tree
ws --config-init
```

## Options

- `--config-init`: write the default `[ws]` config into the shared config file

## Config

Default generated config:

```toml
[ws]
fzf_prompt = "ws> "

[ws.engines.g]
name = "Google"
url = "https://www.google.com/search?q={query}"

[ws.engines.gh]
name = "GitHub"
url = "https://github.com/search?q={query}"

[ws.engines.ytb]
name = "YouTube"
url = "https://www.youtube.com/results?search_query={query}"

[ws.engines.scholar]
name = "Google Scholar"
url = "https://scholar.google.com/scholar?q={query}"
```

When the first argument is a configured engine key, `ws` uses that engine
directly. Otherwise it opens `fzf` to choose an engine. Use `--` when the query
itself starts with an engine key.
