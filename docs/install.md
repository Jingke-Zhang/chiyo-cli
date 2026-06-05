# Installation

Chiyo CLI uses development installation during the v0.x series.

The repository remains the source of truth. `install.sh` creates symlinks from
user-local directories back into this checkout, so editing the repository changes
the installed commands immediately.

## Install

```sh
./install.sh
```

The installer creates:

```text
~/.local/bin/
~/.local/share/zsh/site-functions/
```

Commands are linked into `~/.local/bin`:

```text
bm
app
ws
chiyo
gop-select
```

zsh completions are linked into `~/.local/share/zsh/site-functions`.

`gop` is provided as a shell function because changing directory must happen in
the current shell process.

## Shell Setup

Make sure `~/.local/bin` is in `PATH`:

```zsh
export PATH="$HOME/.local/bin:$PATH"
```

Then load Chiyo shell integration:

```zsh
eval "$(chiyo init zsh)"
```

## Repository Moves

Because installed files are symlinks, moving the repository breaks those links.
After moving the checkout, run:

```sh
./install.sh
```

from the new repository location.

## Non-goals

v0.x does not provide Homebrew, PyPI, Cargo, system-wide installation, automatic
`.zshrc` edits, or a copied `~/.local/share/chiyo-cli` install tree.
