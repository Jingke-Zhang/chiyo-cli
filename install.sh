#!/bin/sh
set -eu

REPO_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
CHIYO_BIN="${BIN_DIR}/chiyo"
ZSHRC="${ZDOTDIR:-$HOME}/.zshrc"
SHELL_INTEGRATION='eval "$(chiyo init zsh)"'

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
missing_dependencies=""
needs_path_setup=0
needs_zsh_setup=0

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

  printf '  %s%-7s%s %s%s%s\n' "$color" "$label" "$reset" "$target" "$dim" "$reset"

  if [ -n "$source" ]; then
    printf '          %s-> %s%s\n' "$dim" "$source" "$reset"
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

active_shell_integration_exists() {
  [ -f "$ZSHRC" ] || return 1

  awk -v line="$SHELL_INTEGRATION" '
    index($0, line) {
      candidate = $0
      sub(/^[ \t]*/, "", candidate)
      if (substr(candidate, 1, 1) != "#") {
        found = 1
      }
    }
    END { exit found ? 0 : 1 }
  ' "$ZSHRC"
}

commented_shell_integration_exists() {
  [ -f "$ZSHRC" ] || return 1

  awk -v line="$SHELL_INTEGRATION" '
    index($0, line) {
      candidate = $0
      sub(/^[ \t]*/, "", candidate)
      if (substr(candidate, 1, 1) == "#") {
        found = 1
      }
    }
    END { exit found ? 0 : 1 }
  ' "$ZSHRC"
}

check_path_setup() {
  if path_contains_bin_dir; then
    status "ok" "$green" "$BIN_DIR is in PATH" ""
    return
  fi

  status "todo" "$yellow" "$BIN_DIR is not in PATH" ""
  todo_count=$((todo_count + 1))
  needs_path_setup=1
}

check_shell_integration() {
  if active_shell_integration_exists; then
    if [ "$mode" = "uninstall" ]; then
      status "todo" "$yellow" "$ZSHRC" "remove: $SHELL_INTEGRATION"
      todo_count=$((todo_count + 1))
      return
    fi

    status "ok" "$green" "$ZSHRC" "$SHELL_INTEGRATION"
    return
  fi

  if [ "$mode" = "uninstall" ]; then
    status "ok" "$green" "$ZSHRC" "no active Chiyo shell integration found"
    return
  fi

  needs_zsh_setup=1
  todo_count=$((todo_count + 1))

  if commented_shell_integration_exists; then
    status "todo" "$yellow" "$ZSHRC" "line exists but is commented: $SHELL_INTEGRATION"
    return
  fi

  status "todo" "$yellow" "$ZSHRC" "$SHELL_INTEGRATION"
}

record_missing_dependency() {
  dependency="$1"

  if [ -z "$missing_dependencies" ]; then
    missing_dependencies="$dependency"
  else
    missing_dependencies="$missing_dependencies $dependency"
  fi
}

check_command_dependency() {
  label="$1"
  command_name="$2"

  path="$(command -v "$command_name" 2>/dev/null || true)"

  if [ -n "$path" ]; then
    status "ok" "$green" "$label" "$path"
    return 0
  fi

  status "missing" "$yellow" "$label" "command not found: $command_name"
  warning_count=$((warning_count + 1))
  record_missing_dependency "$label"
  return 1
}

check_python_dependency() {
  path="$(command -v python3 2>/dev/null || true)"

  if [ -z "$path" ]; then
    path="$(command -v python 2>/dev/null || true)"
  fi

  if [ -n "$path" ]; then
    status "ok" "$green" "python" "$path"
    return
  fi

  status "missing" "$yellow" "python" "command not found: python3 or python"
  warning_count=$((warning_count + 1))
  record_missing_dependency "python"
}

print_next_steps() {
  if [ "$mode" = "uninstall" ]; then
    return
  fi

  section "Next steps"

  if [ "$needs_path_setup" -eq 1 ]; then
    cat <<'EOF'
  Add ~/.local/bin to your shell config:

    export PATH="$HOME/.local/bin:$PATH"

EOF
  fi

  if [ -n "$missing_dependencies" ]; then
    printf '  Install missing dependencies: %s\n\n' "$missing_dependencies"
  fi

  if [ "$needs_zsh_setup" -eq 1 ]; then
    cat <<EOF
  Add active zsh integration to $ZSHRC:

    $SHELL_INTEGRATION

EOF
  fi

  cat <<'EOF'
  Initialize Chiyo config:

    chiyo config init --all --append

  Install tools when you want direct commands:

    chiyo install ws
    chiyo install gop
    chiyo install proj

EOF
}

headline

if [ "$mode" = "install" ]; then
  section "Bootstrap"
  ensure_dir "$BIN_DIR"
  link_item "$REPO_DIR/bin/chiyo" "$CHIYO_BIN"
else
  section "Bootstrap"
  remove_item "$REPO_DIR/bin/chiyo" "$CHIYO_BIN"
fi

section "Environment"
if [ "$mode" = "install" ]; then
  check_path_setup
else
  status "ok" "$green" "PATH" "not changed by install.sh"
fi
check_shell_integration

if [ "$mode" = "install" ]; then
  section "Dependencies"
  check_python_dependency
  check_command_dependency "fd" "fd"
  check_command_dependency "rg" "rg"
  check_command_dependency "fzf" "fzf"
fi

print_next_steps

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
