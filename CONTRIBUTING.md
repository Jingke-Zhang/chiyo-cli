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

## Documentation

When changing user-facing behavior, update the relevant file in `docs/` and add
a short `CHANGELOG.md` entry under `Unreleased`.
