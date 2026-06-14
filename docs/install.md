# Installation

Chiyo CLI uses development installation during the v0.x series.

The repository remains the source of truth. `install.sh` only bootstraps the
`chiyo` command into `~/.local/bin`. Tool wrappers, zsh completions, and shell
functions are installed later through `chiyo install TOOL`.

## Install

```sh
./install.sh
```

The installer is safe to run repeatedly. An existing `chiyo` link that already
points to this repository is skipped, an outdated `chiyo` link is updated, and a
regular file at `~/.local/bin/chiyo` is left untouched with a warning.

The installer also checks whether `~/.zshrc` already contains an active,
uncommented shell integration line:

```zsh
eval "$(chiyo init zsh)"
```

If the line is missing or only appears in a commented line, it is reported as a
todo. The installer does not edit shell config files automatically.

The installer creates:

```text
~/.local/bin/
```

Only `chiyo` is linked into `~/.local/bin`:

```text
chiyo
```

Tool installation is delegated to Chiyo:

```sh
chiyo install s
chiyo install gop
chiyo install proj
```

For ordinary tools, `chiyo install TOOL` creates a direct wrapper and generated
completion. For shell-sensitive tools such as `gop` and `proj`, it installs a
shell function and generated completion; the function calls `chiyo shell TOOL`
so `cd` actions can affect the parent shell.

## Shell Setup

Make sure `~/.local/bin` is in `PATH`:

```zsh
export PATH="$HOME/.local/bin:$PATH"
```

Then load Chiyo shell integration:

```zsh
eval "$(chiyo init zsh)"
```

Initialize explicit default config separately:

```sh
chiyo config init --all --append
```

## Uninstall

```sh
./install.sh --uninstall
```

Uninstall removes only the `chiyo` bootstrap symlink when it points back to the
current repository. Tool wrappers, completions, and shell functions are managed
with `chiyo uninstall TOOL`.

## Repository Moves

Because installed files are symlinks, moving the repository breaks those links.
After moving the checkout, run:

```sh
./install.sh
```

from the new repository location.

## Troubleshooting

Run diagnostics first:

```sh
chiyo doctor
```

If Python, `fd`, `rg`, or `fzf` is reported as missing, install it and make sure
it is visible in `PATH`.

If `bm` cannot read bookmarks, grant Full Disk Access to the terminal app you
use with Chiyo CLI. Also check that Safari bookmarks exist, or configure `bm`
to read another compatible bookmarks plist.

If `app` cannot find installed applications, confirm that Spotlight indexing is
available and that your terminal app has Full Disk Access.

If `gop` or `proj` returns no results, check the configured search roots in
`~/.config/chiyo-cli/tools.toml`. Missing roots are skipped with warnings.

If commands stop working after moving the repository, rerun `./install.sh` from
the new checkout path so symlinks point to the current repository.

## Non-goals

v0.x does not provide Homebrew, PyPI, Cargo, system-wide installation, automatic
`.zshrc` edits, or a copied `~/.local/share/chiyo-cli` install tree. Homebrew is
the preferred future distribution path.
