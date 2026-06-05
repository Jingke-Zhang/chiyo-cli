# Changelog

## v0.1.1

- Improved the development installer with colorful grouped output.
- Made repeated installs idempotent by skipping links that already point to the current repository.
- Added safe uninstall support through `./install.sh --uninstall`.
- Added shell integration checks for `eval "$(chiyo init zsh)"` in `~/.zshrc`.

## v0.1.0

- Initial development-install release.
- Added `bm`, `app`, `gop`, `ws`, and `chiyo`.
- Added zsh completions and symlink-based installation.
