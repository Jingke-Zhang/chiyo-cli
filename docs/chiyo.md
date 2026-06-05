# chiyo

`chiyo` manages shell integration and local diagnostics.

```sh
chiyo init zsh
chiyo doctor
```

## Commands

- `init zsh`: print zsh integration code for completions and shell functions
- `doctor`: check common dependencies and setup paths

`init zsh` does not add `~/.local/bin` to `PATH`. The development installer
creates symlinks there, but users should manage PATH in their own shell config.

`doctor` checks external dependencies, development-install symlinks in
`~/.local/bin`, zsh completion links, `PATH`, `~/.zshrc` integration, and the
optional shared config file. It reports actionable setup work as `todo` and
stale or unsafe install state as `warn`.
