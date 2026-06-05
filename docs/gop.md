# gop

`gop` selects files and directories with `fd` and `fzf`. The helper
`gop-select` prints the selected path, while the zsh function decides the
action: directories are opened with `cd`, and everything else is opened with
macOS `open`.

```sh
gop
gop project
gop -r ~/Documents project
gop --exclude node_modules project
gop --confirm project
gop --config-init
```

## Options

- `-r, --root DIR`: search this directory instead of configured roots; repeat to search multiple directories
- `-E, --exclude PATTERN`: exclude an `fd` glob pattern; repeat to exclude multiple patterns
- `--confirm`: always confirm the selected path in `fzf`
- `--config-init`: write the default `[gop]` config into the shared config file

## Display Colors

- directories: bold blue
- regular files: plain
- executables: bold green

## Config

Default generated config:

```toml
[gop]
roots = ["~/Documents", "~/Downloads", "~/Desktop"]
exclude = ["Library", "node_modules", "OrbStack"]
fzf_prompt = "gop> "
```

Missing search roots are skipped with a warning. If no configured roots exist,
`gop` exits with an error.

Edit `roots` to control the search range and `exclude` to skip large or noisy
directories:

```toml
[gop]
roots = ["~/Documents", "~/Downloads"]
exclude = ["Library", "node_modules", "OrbStack"]
```
