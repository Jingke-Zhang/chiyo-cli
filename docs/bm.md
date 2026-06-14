# bm

`bm` opens Safari bookmarks from the terminal. It reads Safari's
`Bookmarks.plist`, shows matching bookmark paths and URLs in `fzf`, and opens
the selected URL in your configured browser.

When a query matches exactly one bookmark, `bm` opens it directly.
Filtering uses normalized bookmark display paths only; URLs are displayed but
not searched, including during interactive `fzf` filtering.

```sh
chiyo run bm
chiyo run bm github
chiyo run bm --print-url github
chiyo run bm --browser "Google Chrome" github
chiyo run bm --confirm github
chiyo config init bm --append
chiyo run bm --list-completions
chiyo install bm
chiyo doc bm
```

## Options

- `--print-url`: print the selected URL instead of opening it
- `--browser NAME`: open the selected URL with a browser for this run
- `--confirm`: always confirm the selected bookmark in `fzf`
- `--list-completions`: print bookmark display paths for shell completion

## Config

`chiyo config init bm --append` creates this tool's config section in:

```text
~/.config/chiyo-cli/tools.toml
```

Default generated config:

```toml
[bm]
bookmarks_path = "~/Library/Safari/Bookmarks.plist"
skip_folders = ["Bookmarks", "BookmarksMenu", "Tab Group Favorites", "com.apple.ReadingList", "Reading List"]
fzf_prompt = "bm> "
browser = "Safari"
```

Optional folder renaming can be added manually when you want shorter display
paths:

```toml
[bm.rename_folders]
BookmarksBar = "Personal"
Favorites = "Personal"
```

Bookmark source override can be edited in the existing `[bm]` table:

```toml
bookmarks_path = "~/path/to/compatible/Bookmarks.plist"
```

## Completion Data

`chiyo run bm --list-completions` prints one normalized bookmark path per line.
Folder skip and rename rules are applied before candidates are printed.

## Framework Entry

`bm` is a framework-backed built-in. `chiyo run bm ...` reads `[bm]` from
`tools.toml`; `chiyo install bm` creates an optional direct wrapper and
completion.
