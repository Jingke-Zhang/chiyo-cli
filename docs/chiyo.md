# chiyo

`chiyo` manages shell integration and local diagnostics.

```sh
chiyo init zsh
chiyo config init --all --write
chiyo config init ws --force
chiyo config init app --append
chiyo doctor
```

## Commands

- `init zsh`: print zsh integration code for completions and shell functions
- `config init`: write explicit default config for selected tools
- `doctor`: check common dependencies and setup paths

`config init` requires either `--all` or at least one tool name. Its write modes
are:

- `--write`: write only when the config file is missing or empty; this is the default
- `--append`: add missing tool sections and fill missing default keys in
  existing sections without replacing user values
- `--force`: replace selected tool sections

`init zsh` does not add `~/.local/bin` to `PATH`. The development installer
creates symlinks there, but users should manage PATH in their own shell config.

`doctor` checks external dependencies, shell integration files,
development-install symlinks in `~/.local/bin`, zsh completion links, `PATH`,
`~/.zshrc` integration, and the optional shared config file. It reports
actionable setup work as `todo` and stale or unsafe install state as `warn`.
