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

  if [ -d "$target" ]; then
    cd "$target" || return
  else
    open "$target"
  fi
}
