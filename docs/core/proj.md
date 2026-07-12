# proj

`proj` switches to a project directory from the terminal. It discovers
directories that contain project marker paths, selects a project with direct
matching or `fzf`, and emits `cd` shell code for the parent shell.

```sh
chiyo install proj
proj
proj chiyo
proj -r ~/Documents/01-projects cli
proj --exclude node_modules cli
proj --confirm cli
chiyo config init proj --append
chiyo run proj --list-completions
chiyo shell proj cli
chiyo doc proj
```

## Options

- `-r, --root DIR`: search this directory instead of configured roots; repeat to search multiple directories
- `-E, --exclude PATTERN`: exclude an `fd` glob pattern; repeat to exclude multiple patterns
- `--confirm`: always confirm the selected project in `fzf`
- `--list-completions`: print project names for shell completion

## Config

Default generated config:

```toml
["shiori-route/project"]
cmds = ["proj"]
roots = ["~/Documents", "~/Projects", "~/Developer"]
markers = [".project", ".git"]
exclude = ["node_modules", "Library", ".cache"]
fzf_prompt = "proj> "
```

Marker names are configurable. A directory is considered a project when it
contains any configured marker.

Missing search roots are skipped with a warning. If no configured roots exist,
`proj` exits with an error.

In `fzf`, project names and paths are displayed as aligned columns. Fuzzy search
only matches the project name column; paths are shown for disambiguation.

## Completion Data

`proj` is installed as a shell function, so its completion script asks
`chiyo run proj --list-completions` for project names. The completion command
prints one project name per line.

## Framework Entry

`proj` is a framework-backed built-in. `chiyo shell proj ...` reads `["shiori-route/project"]`
from `tools.toml` and prints shell-safe `cd ...` code for shell integration.
