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
- Keep Chiyo infrastructure configuration in
  `~/.config/chiyo-cli/config.toml`, and tool-specific configuration in
  `~/.config/chiyo-cli/tools.toml`.
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

Prefer doing data work in Python before invoking fzf: filter objects with
`filter_item`, sort them with `sort_key`, and render them with
`display_fields`. Use `choose_item_from` for this function-oriented path. fzf
should mostly act as the terminal picker for rows Python has already prepared.

Do not make every visible column searchable unless that is truly the desired
behavior. `choose_item` has these display and search interfaces:

- `rows`: display rows, shown to the user through `fzf --with-nth`
- `display_fields`: a callable that renders one Python object into visible
  `Field` cells
- `search_display_fields`: 1-based visible columns to search
- `filter_rows`: hidden search rows, matched by `fzf --nth`, for text that is
  not visible but should remain searchable

This lets a tool show context such as paths or URLs for disambiguation without
making those fields searchable. For example:

```python
selected = choose_item_from(
    apps,
    config["fzf_prompt"],
    "an application",
    fail,
    display_fields=lambda app: [
        Field(app["name"], STYLE_PRIMARY),
        Field(app["path"], STYLE_SECONDARY),
    ],
    search_display_fields=[1],
)
```

Use `filter_rows` when the searchable text is not already visible, such as an
absolute path behind a compact displayed path. Use the older
`search_field_numbers` argument only when maintaining existing code that
deliberately passes raw fzf field numbers.

For very large data sets, streaming tools may write fzf input incrementally.
They should still reuse `format_row`, `field_widths`, and the same row layout:
visible fields first, hidden filter fields next, hidden `#index` last.

## Documentation

When changing user-facing behavior, update the relevant file in `docs/` and add
a short `CHANGELOG.md` entry under `Unreleased`.
