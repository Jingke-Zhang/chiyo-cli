gop() {
  case "$1" in
    -h|--help|--config-init)
      gop-select "$@"
      return
      ;;
  esac

  local target
  target="$(gop-select "$@")" || return

  [ -z "$target" ] && return

  # cd must happen in the caller's shell, so the Python helper only selects and
  # prints a path. Files can be delegated to macOS open from here.
  if [ -d "$target" ]; then
    cd "$target" || return
  else
    open "$target"
  fi
}
