# app

`app` launches installed macOS applications from the terminal. It discovers
application bundles with Spotlight metadata, shows matching application names,
aliases, and paths in `fzf`, and opens the selected application path.

When a query matches exactly one application, `app` opens it directly. An exact
alias match launches the configured application without opening `fzf`.

```sh
app
app safari
app browser
app --print-name safari
app --confirm browser
app --config-init
app --list-completions
```

## Options

- `--print-name`: print the selected application name instead of opening it
- `--confirm`: always confirm the selected application in `fzf`
- `--config-init`: write the default `[app]` config into the shared config file
- `--list-completions`: print discovered application names for shell completion

## Config

Default generated config:

```toml
[app]
fzf_prompt = "app> "

[app.alias]
```

Optional aliases can be added manually:

```toml
[app.alias]
browser = "Safari"
editor = "Emacs"
terminal = "Ghostty"
```

When more than one application has the same name, `app` keeps each discovered
path as a separate selectable result.

## Completion Data

`app --list-completions` prints one discovered application name per line. The
data comes from Spotlight metadata, so installed application changes are picked
up without editing completion scripts.
