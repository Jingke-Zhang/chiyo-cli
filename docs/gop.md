# gop

`gop` selects files and directories with `fd` and `fzf`. It is shell-sensitive:
directories emit `cd` shell code, while regular files and executables emit
`open` shell code.

```sh
chiyo install gop
gop
gop project
gop -r ~/Documents project
gop --exclude node_modules project
gop --confirm project
chiyo config init gop --append
chiyo run gop --list-completions
chiyo shell gop project
chiyo doc gop
```

## Options

- `-r, --root DIR`: search this directory instead of configured roots; repeat to search multiple directories
- `-E, --exclude PATTERN`: exclude an `fd` glob pattern; repeat to exclude multiple patterns
- `--confirm`: always confirm the selected path in `fzf`
- `--list-completions`: print path candidates for shell completion

## Display Colors

- directories: bold blue
- regular files: plain
- executables: bold green

In `fzf`, `gop` displays compact paths, searches both compact and absolute path
forms, and returns the exact absolute path to the shell function.

## Config

Default generated config:

```toml
["chiyo/gop"]
cmds = ["gop"]
roots = ["~/Documents", "~/Downloads", "~/Desktop"]
exclude = ["Library", "node_modules", "OrbStack"]
fzf_prompt = "gop> "
```

Missing search roots are skipped with a warning. If no configured roots exist,
`gop` exits with an error.

Edit `roots` to control the search range and `exclude` to skip large or noisy
directories:

```toml
["chiyo/gop"]
roots = ["~/Documents", "~/Downloads"]
exclude = ["Library", "node_modules", "OrbStack"]
```

## Completion Data

`gop` is installed as a shell function, so its completion script asks
`chiyo run gop --list-completions` for path candidates. The completion command
prints compact paths from configured roots, one per line.

## Framework Entry

`gop` is a framework-backed built-in. `chiyo shell gop ...` reads `["chiyo/gop"]` from
`tools.toml`, reuses the streaming selector, and prints shell-safe `cd ...` or
`open ...` code for shell integration.
