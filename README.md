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

For zsh, put that line in `~/.zshrc`, then reload your shell.

Install shell integrations:

```sh
chiyo init zsh >> ~/.zshrc
source ~/.zshrc
```

Check local setup:

```sh
chiyo doctor
```

## Tools

### chiyo

`chiyo` manages shell integration and local diagnostics.

```sh
chiyo init zsh
chiyo doctor
```

Useful commands:

- `init zsh`: print zsh initialization code for shell functions
- `doctor`: check common dependencies and setup paths

### bm

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
```

Useful options:

- `--print-url`: print the selected URL instead of opening it
- `--browser NAME`: open the selected URL with a browser for this run
- `--confirm`: always confirm the selected bookmark in `fzf`
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

### app

`app` launches installed macOS applications from the terminal. It discovers
application bundles with Spotlight metadata, shows matching application names,
aliases, and paths in `fzf`, and opens the selected application path.
When a query matches exactly one application, `app` opens it directly. An exact
alias match launches the configured application without opening `fzf`.

```sh
app
app safari
app browser
app --print-name safari
app --confirm browser
app --config-init
```

Useful options:

- `--print-name`: print the selected application name instead of opening it
- `--confirm`: always confirm the selected application in `fzf`
- `--config-init`: write the default `[app]` config into the shared config file

Default generated config:

```toml
[app]
fzf_prompt = "app> "
```

Optional aliases can be added manually:

```toml
[app.alias]
browser = "Safari"
editor = "Emacs"
terminal = "Ghostty"
```

When more than one application has the same name, `app` keeps each discovered
path as a separate selectable result.

### gop

`gop` selects files and directories with `fd` and `fzf`. The helper
`gop-select` prints the selected path, while the zsh function decides the
action: directories are opened with `cd`, and everything else is opened with
macOS `open`.

```sh
gop
gop project
gop --confirm project
gop --config-init
```

Useful options:

- `--confirm`: always confirm the selected path in `fzf`
- `--config-init`: write the default `[gop]` config into the shared config file

Default generated config:

```toml
[gop]
roots = ["~"]
fzf_prompt = "gop> "
```

Edit `roots` to control the search range:

```toml
[gop]
roots = ["~/Documents", "~/Downloads"]
```

## Requirements

- macOS
- Python 3
- `fd`
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
