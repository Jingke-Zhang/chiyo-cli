# proj

`proj` switches to a project directory from the terminal. The helper
`proj-select` discovers directories that contain project marker paths, selects a
project with direct matching or `fzf`, and prints the selected directory. The
zsh function then `cd`s there.

```sh
proj
proj chiyo
proj -r ~/Documents/01-projects cli
proj --exclude node_modules cli
proj --confirm cli
proj-select --config-init
proj-select --list-completions
```

## Options

- `-r, --root DIR`: search this directory instead of configured roots; repeat to search multiple directories
- `-E, --exclude PATTERN`: exclude an `fd` glob pattern; repeat to exclude multiple patterns
- `--confirm`: always confirm the selected project in `fzf`
- `--config-init`: write the default `[proj]` config into the shared config file
- `--list-completions`: print project names for shell completion

## Config

Default generated config:

```toml
[proj]
roots = ["~/Documents", "~/Projects", "~/Developer"]
markers = [".project", ".git"]
exclude = ["node_modules", "Library", ".cache"]
fzf_prompt = "proj> "
```

Marker names are configurable. A directory is considered a project when it
contains any configured marker.

Missing search roots are skipped with a warning. If no configured roots exist,
`proj-select` exits with an error.

In `fzf`, project names and paths are displayed as aligned columns. Fuzzy search
only matches the project name column; paths are shown for disambiguation.

## Completion Data

`proj` is a shell function, so its completion script asks `proj-select` for
project names. `proj-select --list-completions` prints one project name per line.
