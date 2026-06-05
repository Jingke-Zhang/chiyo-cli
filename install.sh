#!/bin/sh
set -eu

REPO_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
ZSH_COMPLETIONS_DIR="${HOME}/.local/share/zsh/site-functions"

commands="bm app ws chiyo gop-select"
completions="_bm _app _ws _gop"

mkdir -p "$BIN_DIR"
mkdir -p "$ZSH_COMPLETIONS_DIR"

for command in $commands; do
  ln -sf "$REPO_DIR/bin/$command" "$BIN_DIR/$command"
  printf 'linked %s -> %s\n' "$BIN_DIR/$command" "$REPO_DIR/bin/$command"
done

for completion in $completions; do
  if [ -f "$REPO_DIR/completions/$completion" ]; then
    ln -sf "$REPO_DIR/completions/$completion" "$ZSH_COMPLETIONS_DIR/$completion"
    printf 'linked %s -> %s\n' "$ZSH_COMPLETIONS_DIR/$completion" "$REPO_DIR/completions/$completion"
  fi
done

if ! command -v bm >/dev/null 2>&1; then
  cat <<'EOF'

Please add ~/.local/bin to your PATH.

For zsh:

  export PATH="$HOME/.local/bin:$PATH"

EOF
fi

cat <<'EOF'
Add this to ~/.zshrc to load shell functions and completions:

  eval "$(chiyo init zsh)"

gop is a shell function, so it becomes available after the zsh integration is loaded.
EOF
