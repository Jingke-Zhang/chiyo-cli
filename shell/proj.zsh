proj() {
  case "$1" in
    -h|--help)
      proj-select "$@"
      return
      ;;
  esac

  local target

  if [ "$#" -eq 1 ] && [ -d "$1" ]; then
    target="$1"
  else
    target="$(proj-select "$@")" || return
  fi

  [ -z "$target" ] && return
  cd "$target" || return
}
