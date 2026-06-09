# Changelog

## Unreleased

- Added a standard `make test` entrypoint for local development.
- Added GitHub Actions CI on macOS.
- Added project metadata in `pyproject.toml`.
- Added contributor and security documentation.
- Expanded README project status, development, and security guidance.
- Expanded `.gitignore` for Python and macOS local artifacts.
- Clarified post-install config setup and macOS Full Disk Access requirements.
- Added install troubleshooting and release process documentation.

## v0.1.2

- Deepened `chiyo doctor` checks for development-install symlinks, zsh
  completion links, `PATH`, zsh integration, and config state.
- Added `proj-select`, the `proj` zsh function, `_proj` completion support,
  installer wiring, doctor checks, documentation, and tests.
- Added configurable project markers for `proj`, with `.project` and `.git`
  defaults, aligned `fzf` rows, and project-name-only fuzzy matching.
- Treated configured tool tables as explicit user config, with warnings when
  missing keys fall back to defaults.
- Changed config initialization to write full defaults and avoid silently
  merging default `ws` engines into user-owned config.
- Added shared colored warning output that respects `NO_COLOR` and plain stderr.
- Added unified `chiyo config init` with explicit tool selection and `--write`,
  `--append`, and `--force` modes.

## v0.1.1

- Improved the development installer with colorful grouped output.
- Made repeated installs idempotent by skipping links that already point to the current repository.
- Added safe uninstall support through `./install.sh --uninstall`.
- Added shell integration checks for `eval "$(chiyo init zsh)"` in `~/.zshrc`.

## v0.1.0

- Initial development-install release.
- Added `bm`, `app`, `gop`, `ws`, and `chiyo`.
- Added zsh completions and symlink-based installation.
