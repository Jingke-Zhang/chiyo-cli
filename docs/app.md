# app

`app` launches installed macOS applications from the terminal. It discovers
application bundles with Spotlight metadata, shows matching application names,
aliases, and paths in `fzf`, and opens the selected application path.

When a query matches exactly one application, `app` opens it directly. An exact
alias match launches the configured application without opening `fzf`.
Filtering uses application names and configured aliases; displayed paths are not
searched, including during interactive `fzf` filtering.

```sh
app
app safari
app browser
app --print-name safari
app --confirm browser
chiyo config init app --append
app --list-completions
chiyo run app Safari
chiyo doc app
```

## Options

- `--print-name`: print the selected application name instead of opening it
- `--confirm`: always confirm the selected application in `fzf`
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

## Framework Entry

`app` is also available as a framework-backed built-in tool through
`chiyo run app ...` once `app` is enabled in `[chiyo].enabled_tools`. This entry
reads `[app]` from `tools.toml` and supports generated wrappers through
`chiyo install app`.
