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
