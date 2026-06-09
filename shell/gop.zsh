gop() {
  case "$1" in
    -h|--help)
      gop-select "$@"
      return
      ;;
  esac

  local target

  if [ "$#" -eq 1 ] && [ -e "$1" ]; then
    target="$1"
  else
    target="$(gop-select "$@")" || return
  fi

  [ -z "$target" ] && return

  # cd must happen in the caller's shell, so the Python helper only selects and
  # prints a path. Files can be delegated to macOS open from here.
  if [ -d "$target" ]; then
    cd "$target" || return
  else
    open "$target"
  fi
}
