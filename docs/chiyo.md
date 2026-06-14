# chiyo

`chiyo` manages shell integration and local diagnostics.

```sh
chiyo init zsh
chiyo config init --all --write
chiyo config init s --force
chiyo config init app --append
chiyo tool list
chiyo run s gh chiyo-cli
chiyo shell gop docs
chiyo install s
chiyo doc s
chiyo doctor
```

## Commands

- `init zsh`: print zsh integration code for completions and shell functions
- `config init`: write explicit default config for Chiyo or selected tools
- `tool list|enable|disable`: inspect and control tools available through
  `chiyo run`
- `run TOOL`: run an enabled tool through the framework
- `shell TOOL`: run an enabled shell-action tool and print shell-safe code
- `install TOOL`: install a generated wrapper or shell function plus completion
- `doc TOOL`: print docs embedded in the tool module
- `doctor`: check common dependencies and setup paths

`config init` requires either `--all` or at least one target name. `chiyo`
writes infrastructure defaults to `~/.config/chiyo-cli/config.toml`; tool names
write tool defaults to `~/.config/chiyo-cli/tools.toml`. `--all` initializes
Chiyo plus the currently enabled tools. Fresh config enables `jingke-zhang/go-or-pick` and
`jingke-zhang/web-search` by default.

Its write modes are:

- `--write`: write only when the config file is missing or empty; this is the default
- `--append`: add missing tool sections and fill missing default keys in
  existing sections without replacing user values
- `--force`: replace selected tool sections

`init zsh` does not add `~/.local/bin` to `PATH`. The development installer
creates symlinks there, but users should manage PATH in their own shell config.

`doctor` checks external dependencies, shell integration files,
development-install symlinks in `~/.local/bin`, zsh completion links, `PATH`,
`~/.zshrc` integration, and the config files. It reports
actionable setup work as `todo` and stale or unsafe install state as `warn`.
