# app

`app` launches installed macOS applications from the terminal. It discovers
application bundles with Spotlight metadata, shows matching application names,
aliases, and paths in `fzf`, and opens the selected application path.

When a query matches exactly one application, `app` opens it directly. An exact
alias match launches the configured application without opening `fzf`.
Filtering uses application names and configured aliases; displayed paths are not
searched, including during interactive `fzf` filtering.

```sh
chiyo run app
chiyo run app safari
chiyo run app browser
chiyo run app --print-name safari
chiyo run app --confirm browser
chiyo config init app --append
chiyo run app --list-completions
chiyo install app
chiyo doc app
```

## Options

- `--print-name`: print the selected application name instead of opening it
- `--confirm`: always confirm the selected application in `fzf`
- `--list-completions`: print discovered application names for shell completion

## Config

Default generated config:

```toml
["jingke-zhang/application"]
cmds = ["app"]
fzf_prompt = "app> "

["jingke-zhang/application".alias]
```

Optional aliases can be added manually:

```toml
["jingke-zhang/application".alias]
browser = "Safari"
editor = "Emacs"
terminal = "Ghostty"
```

When more than one application has the same name, `app` keeps each discovered
path as a separate selectable result.

## Completion Data

`chiyo run app --list-completions` prints one discovered application name per
line. The data comes from Spotlight metadata, so installed application changes
are picked up without editing completion scripts.

## Framework Entry

`app` is a framework-backed built-in tool. `chiyo run app ...` reads `["jingke-zhang/application"]`
from `tools.toml`; `chiyo install app` creates an optional direct wrapper and
completion.
