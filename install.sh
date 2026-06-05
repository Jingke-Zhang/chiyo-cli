#!/bin/sh
set -eu

REPO_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
ZSH_COMPLETIONS_DIR="${HOME}/.local/share/zsh/site-functions"

commands="bm app ws chiyo gop-select proj-select"
completions="_bm _app _ws _gop _proj"
zshrc="${ZDOTDIR:-$HOME}/.zshrc"
shell_integration='eval "$(chiyo init zsh)"'

mode="install"

case "${1:-}" in
  "")
    ;;
  --uninstall)
    mode="uninstall"
    ;;
  -h|--help)
    cat <<'EOF'
Usage:
  ./install.sh
  ./install.sh --uninstall
EOF
    exit 0
    ;;
  *)
    printf 'install.sh: unknown option: %s\n' "$1" >&2
    exit 2
    ;;
esac

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  bold="$(printf '\033[1m')"
  green="$(printf '\033[32m')"
  blue="$(printf '\033[34m')"
  yellow="$(printf '\033[33m')"
  red="$(printf '\033[31m')"
  dim="$(printf '\033[2m')"
  reset="$(printf '\033[0m')"
else
  bold=""
  green=""
  blue=""
  yellow=""
  red=""
  dim=""
  reset=""
fi

created_count=0
updated_count=0
skipped_count=0
removed_count=0
todo_count=0
warning_count=0

headline() {
  if [ "$mode" = "uninstall" ]; then
    printf '%sChiyo CLI development uninstall%s\n' "$bold" "$reset"
  else
    printf '%sChiyo CLI development install%s\n' "$bold" "$reset"
  fi

  printf '%srepo:%s %s\n\n' "$dim" "$reset" "$REPO_DIR"
}

section() {
  printf '\n%s%s%s\n' "$bold" "$1" "$reset"
}

status() {
  label="$1"
  color="$2"
  target="$3"
  source="$4"

  printf '  %s%-6s%s %s%s%s\n' "$color" "$label" "$reset" "$target" "$dim" "$reset"

  if [ -n "$source" ]; then
    printf '         %s-> %s%s\n' "$dim" "$source" "$reset"
  fi
}

ensure_dir() {
  dir="$1"

  if [ -d "$dir" ]; then
    status "ok" "$green" "$dir" ""
    return
  fi

  mkdir -p "$dir"
  status "mkdir" "$blue" "$dir" ""
}

link_item() {
  source="$1"
  target="$2"

  if [ ! -e "$source" ]; then
    status "warn" "$yellow" "$target" "missing source: $source"
    warning_count=$((warning_count + 1))
    return
  fi

  if [ -L "$target" ]; then
    current="$(readlink "$target")"

    if [ "$current" = "$source" ]; then
      status "skip" "$green" "$target" "$source"
      skipped_count=$((skipped_count + 1))
      return
    fi

    ln -sf "$source" "$target"
    status "update" "$blue" "$target" "$source"
    updated_count=$((updated_count + 1))
    return
  fi

  if [ -e "$target" ]; then
    status "warn" "$yellow" "$target" "exists and is not a symlink; left untouched"
    warning_count=$((warning_count + 1))
    return
  fi

  ln -s "$source" "$target"
  status "link" "$blue" "$target" "$source"
  created_count=$((created_count + 1))
}

remove_item() {
  source="$1"
  target="$2"

  if [ ! -e "$target" ] && [ ! -L "$target" ]; then
    status "skip" "$green" "$target" "not installed"
    skipped_count=$((skipped_count + 1))
    return
  fi

  if [ ! -L "$target" ]; then
    status "warn" "$yellow" "$target" "exists and is not a symlink; left untouched"
    warning_count=$((warning_count + 1))
    return
  fi

  current="$(readlink "$target")"

  if [ "$current" != "$source" ]; then
    status "skip" "$yellow" "$target" "points elsewhere: $current"
    skipped_count=$((skipped_count + 1))
    return
  fi

  rm "$target"
  status "remove" "$red" "$target" "$source"
  removed_count=$((removed_count + 1))
}

path_contains_bin_dir() {
  case ":$PATH:" in
    *":$BIN_DIR:"*) return 0 ;;
    *) return 1 ;;
  esac
}

check_shell_integration() {
  if [ -f "$zshrc" ] && grep -F "$shell_integration" "$zshrc" >/dev/null 2>&1; then
    if [ "$mode" = "uninstall" ]; then
      status "todo" "$yellow" "$zshrc" "remove: $shell_integration"
      todo_count=$((todo_count + 1))
      cat <<EOF

  ${bold}Remove this from ~/.zshrc if you no longer use Chiyo CLI:${reset}

    $shell_integration
EOF
      return
    fi

    status "ok" "$green" "$zshrc" "$shell_integration"
    return
  fi

  if [ "$mode" = "uninstall" ]; then
    status "ok" "$green" "$zshrc" "no Chiyo shell integration found"
    return
  fi

  status "todo" "$yellow" "$zshrc" "$shell_integration"
  todo_count=$((todo_count + 1))
  cat <<EOF

  ${bold}Add this to ~/.zshrc to load shell functions and completions:${reset}

    $shell_integration
EOF
}

headline

if [ "$mode" = "install" ]; then
  section "Directories"
  ensure_dir "$BIN_DIR"
  ensure_dir "$ZSH_COMPLETIONS_DIR"

  section "Commands"
  for command in $commands; do
    link_item "$REPO_DIR/bin/$command" "$BIN_DIR/$command"
  done

  section "Zsh completions"
  for completion in $completions; do
    link_item "$REPO_DIR/completions/$completion" "$ZSH_COMPLETIONS_DIR/$completion"
  done
else
  section "Commands"
  for command in $commands; do
    remove_item "$REPO_DIR/bin/$command" "$BIN_DIR/$command"
  done

  section "Zsh completions"
  for completion in $completions; do
    remove_item "$REPO_DIR/completions/$completion" "$ZSH_COMPLETIONS_DIR/$completion"
  done
fi

section "Shell setup"
if [ "$mode" = "install" ]; then
  if path_contains_bin_dir; then
    status "ok" "$green" "$BIN_DIR is in PATH" ""
  else
    status "warn" "$yellow" "$BIN_DIR is not in PATH" ""
    warning_count=$((warning_count + 1))
    cat <<'EOF'

  Add this to your shell config:

    export PATH="$HOME/.local/bin:$PATH"
EOF
  fi
fi

check_shell_integration

if [ "$mode" = "install" ]; then
  cat <<'EOF'

  gop is a shell function and becomes available after this integration is loaded.
EOF
fi

section "Summary"
printf '  %screated:%s %s\n' "$blue" "$reset" "$created_count"
printf '  %supdated:%s %s\n' "$blue" "$reset" "$updated_count"
printf '  %sremoved:%s %s\n' "$red" "$reset" "$removed_count"
printf '  %sskipped:%s %s\n' "$green" "$reset" "$skipped_count"
printf '  %stodo:%s %s\n' "$yellow" "$reset" "$todo_count"
printf '  %swarnings:%s %s\n' "$yellow" "$reset" "$warning_count"

if [ "$warning_count" -gt 0 ]; then
  printf '\n%sFinished with warnings.%s\n' "$yellow" "$reset"
elif [ "$todo_count" -gt 0 ]; then
  printf '\n%sFinished with todos.%s\n' "$yellow" "$reset"
elif [ "$mode" = "uninstall" ]; then
  printf '\n%sUninstall complete.%s\n' "$green" "$reset"
else
  printf '\n%sInstall complete.%s\n' "$green" "$reset"
fi
