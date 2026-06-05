# bm

`bm` opens Safari bookmarks from the terminal. It reads Safari's
`Bookmarks.plist`, shows matching bookmark paths and URLs in `fzf`, and opens
the selected URL in your configured browser.

When a query matches exactly one bookmark, `bm` opens it directly.

```sh
bm
bm github
bm --print-url github
bm --browser "Google Chrome" github
bm --confirm github
bm --config-init
bm --list-completions
```

## Options

- `--print-url`: print the selected URL instead of opening it
- `--browser NAME`: open the selected URL with a browser for this run
- `--confirm`: always confirm the selected bookmark in `fzf`
- `--config-init`: write the default `[bm]` config into the shared config file
- `--list-completions`: print bookmark display paths for shell completion

## Config

`bm --config-init` creates or updates this tool's config section in:

```text
~/.config/chiyo-cli/config.toml
```

Default generated config:

```toml
[bm]
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

Advanced bookmark source override can be added to the existing `[bm]` table:

```toml
bookmarks_path = "~/path/to/compatible/Bookmarks.plist"
```

## Completion Data

`bm --list-completions` prints one normalized bookmark path per line. Folder
skip and rename rules are applied before candidates are printed.
