# Contributing

Chiyo CLI is a small personal toolbox, but careful fixes, documentation updates,
tests, and focused new tools are welcome.

## Local Setup

Install the development checkout:

```sh
./install.sh
```

Then load shell integration from your zsh config:

```zsh
eval "$(chiyo init zsh)"
```

Run diagnostics:

```sh
chiyo doctor
```

## Tests

Run the full test suite:

```sh
make test
```

This currently runs:

```sh
python3 -m unittest discover -s tests -v
```

## Tool Design

New tools should stay small and follow the existing shape:

- Search or collect candidates.
- Pick one candidate directly or through `fzf`.
- Perform one clear action.
- Keep configuration in `~/.config/chiyo-cli/config.toml`.
- Expose `--list-completions` when dynamic shell completion is useful.

Prefer readable standard-library Python and small shell integrations over larger
frameworks.

### Reusable Interfaces

Shared helpers live under `chiyo_cli/`. New tools should use these before adding
tool-local parsing, formatting, or setup code:

- `chiyo_cli.config.load_module_config`: load one `[tool]` table with defaults
  and optional missing-key warnings.
- `chiyo_cli.config.init_module_config`: write or replace one tool's default
  config without deleting other tools' tables.
- `chiyo_cli.config.format_module_config`: render simple default config for
  docs, tests, and `chiyo config init`.
- `chiyo_cli.fzf.choose_item`: map fzf selection back to original Python
  objects using a hidden stable index.
- `chiyo_cli.fzf.Field`: define visible cells and optional ANSI styles.

### fzf Display And Filtering

Do not make visible columns double as filtering rules unless that is truly the
desired behavior. `choose_item` has two separate row interfaces:

- `rows`: display rows, shown to the user through `fzf --with-nth`
- `filter_rows`: hidden search rows, matched by `fzf --nth`

This lets a tool show context such as paths or URLs for disambiguation without
making those fields searchable. For example:

```python
rows = [
    [
        Field(app["name"], STYLE_PRIMARY),
        Field(app["path"], STYLE_SECONDARY),
    ]
    for app in apps
]
filter_rows = [[app["name"]] for app in apps]

selected = choose_item(
    apps,
    rows,
    config["fzf_prompt"],
    "an application",
    fail,
    filter_rows=filter_rows,
)
```

Use the older `search_field_numbers` argument only when maintaining existing
code that deliberately searches visible columns by fzf field number. New code
should prefer `filter_rows`, because it survives display-column reordering and
supports normalized or synthetic search fields.

For very large data sets, streaming tools may write fzf input incrementally.
They should still reuse `format_row`, `field_widths`, and the same row layout:
visible fields first, hidden filter fields next, hidden `#index` last.

## Documentation

When changing user-facing behavior, update the relevant file in `docs/` and add
a short `CHANGELOG.md` entry under `Unreleased`.
