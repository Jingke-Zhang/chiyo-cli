# Chiyo CLI

A collection of small search-oriented command-line tools.

Chiyo CLI is a personal toolbox for reaching known objects faster from the
terminal. The tools live in `bin/` and are designed to be small, focused, easy
to read, customizable, and composable with other command-line programs.

## Why

Over the years, I found myself increasingly frustrated with modern software.

This is not because graphical interfaces are bad. GUI applications are often
more intuitive, accessible, and polished than their command-line counterparts.

The problem is that many modern tools have gradually become larger and more
complex than what I actually need.

A typical application often bundles together dozens of features, settings pages,
integrations, background services, and user interface layers. While these
features may be useful for some users, they can also create information overload
and make simple tasks feel unnecessarily heavy.

At the same time, many lightweight tools do exist, but they are often scattered
across different applications, ecosystems, and interfaces. As a result, my
workflow became fragmented.

I wanted something different.

Instead of searching for the perfect application, I started building small tools
that solve one problem at a time.

The goal is not to compete with GUI applications. The goal is to create tools
that are:

- Small and focused
- Easy to understand
- Easy to customize
- Composable with other tools
- Accessible from a single interface: the terminal

For me, the terminal is not simply a replacement for graphical interfaces. It is
a unifying layer that allows many small tools to work together without
introducing yet another application, window, or workflow.

This repository contains those tools. Some are practical. Some are
experimental. All of them are built around the same idea:

Build the smallest tool that solves the problem well enough.

## Install

Add this repository's `bin` directory to your shell path:

```sh
export PATH="$HOME/path/to/chiyo-cli/bin:$PATH"
```

For zsh, put that line in `~/.zshrc`.

## Tools

### bm

`bm` opens Safari bookmarks from the terminal. It reads Safari's
`Bookmarks.plist`, shows matching bookmark paths and URLs in `fzf`, and opens
the selected URL in your configured browser.

```sh
bm
bm github
bm --print-url github
bm --browser "Google Chrome" github
bm --config-init
```

Useful options:

- `--print-url`: print the selected URL instead of opening it
- `--browser NAME`: open the selected URL with a browser for this run
- `--config-init`: write the default `[bm]` config into the shared config file

`bm --config-init` creates or updates this tool's config section in:

```text
~/.config/chiyo-cli/config.toml
```

The config file is optional. If it does not exist, the tool uses defaults from
the script.

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

## Requirements

- macOS
- Python 3
- `fzf`
- Safari bookmarks, unless `bookmarks_path` points to another compatible plist

## Config

All tools in this repository share one config file:

```text
~/.config/chiyo-cli/config.toml
```

Each command owns its own TOML table. For example, `bm` uses `[bm]`. Future tools
can add their own sections without interfering with existing ones.

Shared config loading and initialization helpers live in `chiyo_cli/config.py`.

## License

MIT
