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

## AI-Assisted

This project is built with AI assistance. The tools are intentionally small
enough that generated changes can be read, questioned, and reshaped without
turning the codebase into a black box.

The current code should be treated as not yet fully audited. AI helps with
drafting, refactoring, tests, and documentation, but the final responsibility
for behavior, design, and maintainability stays with me.

## Install

Generate zsh integration from this repository:

```sh
/path/to/chiyo-cli/bin/chiyo init zsh >> ~/.zshrc
```

```sh
source ~/.zshrc
```

Check local setup:

```sh
chiyo doctor
```

## Display Style

Selection UIs use color as lightweight type information, not decoration.
Primary actionable labels use bold green when there is no more specific type
color. Paths and URLs use italic underlining because they point somewhere.

Path-like tools follow a small file palette:

- directories: bold blue
- regular files: plain
- executables: bold green

## Tools

- [`chiyo`](docs/chiyo.md): shell integration and setup diagnostics
- [`bm`](docs/bm.md): search Safari bookmarks and open URLs
- [`app`](docs/app.md): search installed macOS applications and launch one
- [`ws`](docs/ws.md): build web search URLs and open them
- [`gop`](docs/gop.md): search files/directories, then `cd` or `open`

## Future Work

- `proj`: a project switching tool for quickly jumping between known workspaces
- Manual review of the current AI-assisted codebase
- More small search tools that follow the same Search -> Pick -> Action shape

## Requirements

- macOS
- Python 3
- `fd`
- `fzf`
- Safari bookmarks, unless `bm` uses another compatible plist

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
