# zo

`zo` searches Zotero items from the terminal. It first tries Zotero's Local API,
then falls back to a read-only SQLite snapshot of the local Zotero data
directory. Matching items are shown in `fzf` with title, creators, and year, and
the selected item opens in Zotero by default.

When a query matches exactly one item, `zo` opens it directly. Use `--confirm`
to inspect the match in `fzf` first. Query filtering and interactive `fzf`
filtering match item titles only.

```sh
chiyo run zo
chiyo run zo convex optimization
chiyo run zo --open-pdf hazan
chiyo run zo --print-key mp-spdz
chiyo run zo --print-url linear algebra
chiyo run zo --print-path systems
chiyo run zo --source sqlite algorithms
chiyo config init zo --append
chiyo run zo --list-completions
chiyo install zo
chiyo doc zo
```

## Options

- `--source auto|local-api|sqlite`: choose the Zotero data source
- `--open-pdf`: open the selected item's first local PDF attachment
- `--print-key`: print the selected Zotero item key instead of opening it
- `--print-url`: print the selected URL, or DOI URL, instead of opening it
- `--print-path`: print the selected local PDF attachment path
- `--confirm`: always confirm the selected item in `fzf`
- `--list-completions`: print item titles for shell completion

## Zotero Local API

`zo` works best when Zotero's Local API is enabled:

```text
Zotero Settings -> Advanced -> Allow other applications on this computer to communicate with Zotero
```

The Local API runs on `localhost:23119`, works offline, and does not require an
API key. If it is unavailable, `chiyo run zo --source auto` falls back to a
temporary copy of `zotero.sqlite` and reads that copy only.

## Config

`chiyo config init zo --append` creates this tool's config section in:

```text
~/.config/chiyo-cli/tools.toml
```

Default generated config:

```toml
["chiyo/zo"]
cmds = ["zo"]
local_api_url = "http://localhost:23119/api/"
zotero_data_dir = "~/Zotero"
fzf_prompt = "zo> "
```

If your Zotero data directory is customized, edit `zotero_data_dir` to the
directory that contains `zotero.sqlite` and `storage/`.

## Completion Data

`chiyo run zo --list-completions` prints one item title per line. Completion
uses the same data source selection as normal search.

## Framework Entry

`zo` is a framework-backed built-in tool. `chiyo run zo ...` reads `["chiyo/zo"]` from
`tools.toml`; `chiyo install zo` creates an optional direct wrapper and
completion.
