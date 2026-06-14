# Chiyo CLI

A collection of small search-oriented command-line tools.

Chiyo CLI is a personal toolbox for reaching known objects faster from the
terminal. `bin/chiyo` is the bootstrap command; built-in tools live under
`chiyo_cli/builtin_tools`, and user tools live in
`~/.config/chiyo-cli/tools/`. Tools are designed to be small, focused, easy to
read, customizable, and composable with other command-line programs.

## Quick Start

```sh
./install.sh
export PATH="$HOME/.local/bin:$PATH"
eval "$(chiyo init zsh)"
chiyo doctor
```

Try a few commands:

```sh
chiyo run s gh chiyo-cli
chiyo run ws cli-tools
chiyo run app safari
chiyo run bm github
chiyo run zo convex optimization
chiyo shell proj cli-tools
chiyo shell gop docs
```

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

Chiyo CLI currently uses development installation. `install.sh` only bootstraps
the `chiyo` command into `~/.local/bin`; tools, completions, and shell functions
are installed later through `chiyo install TOOLS...`.

```sh
./install.sh
```

Make sure `~/.local/bin` is in your `PATH`:

```sh
export PATH="$HOME/.local/bin:$PATH"
```

Add shell integration to `~/.zshrc`:

```sh
eval "$(chiyo init zsh)"
```

Initialize config and install tools as needed:

```sh
chiyo config init --all --append
chiyo install s ws gop
```

Check local setup:

```sh
chiyo doctor
```

The zsh integration loads shell functions installed by `chiyo install TOOLS...` and
registers zsh completions. It does not manage `PATH`; keep that in your shell
config.

Because installation uses symlinks, moving this repository breaks installed
commands until `./install.sh` is run again from the new location.

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
- [`s`](docs/s.md): build web search URLs and open them
- [`ws`](docs/workspace.md): enter or manage tmux workspaces
- [`zo`](docs/zo.md): search Zotero items and open entries or PDFs
- [`gop`](docs/gop.md): search files/directories, then `cd` or `open`
- [`proj`](docs/proj.md): search git projects, then `cd` into one
- [Installation details](docs/install.md): development install and shell setup
- [Troubleshooting](docs/install.md#troubleshooting): common setup and
  permission issues

## Future Work

- Manual review of the current AI-assisted codebase
- More small search tools that follow the same Search -> Pick -> Action shape

## Project Status

Chiyo CLI is in the v0.x development-install stage. Command behavior is intended
to stay small and understandable, but config details and installation mechanics
may still change before a stable release.

## Requirements

- macOS
- Python 3
- `fd`
- `rg`
- `fzf`
- Safari bookmarks, unless `bm` uses another compatible plist
- Zotero data, unless `zo` uses only the Zotero Local API
- Full Disk Access for your terminal app on macOS, so Chiyo can read bookmarks,
  application metadata, and configured filesystem roots

## Config

Chiyo uses two config files:

```text
~/.config/chiyo-cli/config.toml
~/.config/chiyo-cli/tools.toml
```

`config.toml` stores Chiyo infrastructure settings, such as enabled tools.
`tools.toml` stores tool-specific settings. Tool sections use the stable
`author_id/tool_name` identity, for example `["jingke-zhang/explorer-bookmark"]`.
Identity parts are normalized to lowercase, with spaces and punctuation
converted to `-`.

Use `chiyo config init` to write explicit default config:

```sh
chiyo config init --all --write
chiyo config init s --force
chiyo config init app --append
```

`chiyo config init` requires either `--all` or at least one tool name. The
default `--write` mode only writes when the config file is missing or empty.
Use `--append` to add missing tool sections and fill missing default keys in
existing sections without replacing user values. Use `--force` to replace
selected sections.

`chiyo config init --all` initializes Chiyo plus the currently enabled tools.
Fresh config enables `jingke-zhang/go-or-pick` and `jingke-zhang/web-search` by default. A tool section can
set `cmds = ["bm", "bookmarks"]`; any configured command in that list can be
used with `chiyo run` or installed as a wrapper, as long as no enabled tool
claims the same command.
Configured commands must match `^[a-z][a-z0-9-]*$`; invalid entries are reported
by `chiyo tool list` and `chiyo doctor`.

Generated config is meant to be edited. If a command table exists, Chiyo treats
it as explicit user config: missing keys fall back to code defaults with a
warning, but configured lists and tables are not silently merged with default
choices.

Shared config loading and initialization helpers live in `chiyo_cli/config.py`.

## Completions

Tools that support dynamic shell completion expose a common interface:

```sh
chiyo run <tool> --list-completions
```

The command prints plain text candidates, one per line. Generated zsh
completion files call this interface instead of parsing config files or
platform data directly.

## Development

Run the test suite:

```sh
make test
```

This repository uses GitHub Actions to run the same test command on macOS.
Contributions should keep tool behavior focused, documented, and covered by
tests where practical. See [CONTRIBUTING.md](CONTRIBUTING.md) for details.
See [docs/release.md](docs/release.md) for the release checklist.

Shared implementation interfaces live in `chiyo_cli/`. New tools should
subclass `chiyo_cli.toolkit.PickOpenTool`, use `default_config` for generated
`tools.toml` sections, and rely on the framework for common argument parsing,
filtering, completion, selection, and action execution.

## Security

Chiyo CLI runs locally but may read local bookmarks, application metadata,
configured filesystem roots, and shared config. See [SECURITY.md](SECURITY.md)
for the local data and external-action model.

On macOS, grant Full Disk Access to the terminal app you use with Chiyo CLI.
Without it, commands such as `bm` and `app` may be unable to read Safari
bookmarks or application data even when the command itself is installed
correctly.

## License

MIT
