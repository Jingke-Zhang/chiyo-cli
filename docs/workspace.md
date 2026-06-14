# ws

`ws` manages tmux workspaces. It can attach to an existing tmux session,
switch clients from inside tmux, or create a new session from a configured
alias or discovered project directory.

```sh
chiyo run ws
chiyo run ws cli-tools
chiyo run ws --new notes ~/Documents/notes
chiyo run ws --kill cli-tools
chiyo run ws --rename old-name new-name
chiyo config init ws --append
chiyo run ws --list-completions
chiyo install ws
```

## Options

- `--new NAME PATH`: create a tmux session for `PATH` and enter it
- `--kill QUERY`: select or match an existing tmux session and kill it
- `--rename OLD NEW`: rename an existing tmux session
- `-r, --root DIR`: search this directory instead of configured roots; repeat to search multiple directories
- `-E, --exclude PATTERN`: exclude a glob pattern from project search; repeat to exclude multiple patterns
- `--confirm`: always confirm the selected workspace in `fzf`
- `--list-completions`: print workspace names for shell completion

## Config

Default generated config:

```toml
["jingke-zhang/workspace"]
cmds = ["ws"]
roots = ["~/Documents", "~/Projects", "~/Developer"]
markers = [".project", ".git"]
exclude = ["node_modules", "Library", ".cache"]
session_prefix = ""
fzf_prompt = "ws> "

["jingke-zhang/workspace".alias]
```

Aliases map short names to directories:

```toml
["jingke-zhang/workspace".alias]
cli = "~/Documents/01-projects/cli-tools"
notes = "~/Documents/notes"
```

Project discovery uses the same marker model as `proj`: a directory is a
workspace candidate when it contains one of the configured marker files.

## Behavior

When the selected workspace already has a tmux session, `ws` enters that
session. Outside tmux it runs `tmux attach-session`; inside tmux it runs
`tmux switch-client`. When the selected alias or project does not have a
session yet, `ws` creates one with `tmux new-session -d` and then enters it.
