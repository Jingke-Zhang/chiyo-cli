# Security

Chiyo CLI is designed to run locally. It does not upload local data or call a
remote service on its own, but individual tools may open URLs or local
applications based on your command input and configuration.

## Local Data Access

Depending on the command, Chiyo CLI may read:

- Safari bookmarks or another configured bookmarks plist for `bm`.
- Spotlight application metadata for `app`.
- Configured filesystem roots for `gop` and `proj`.
- `~/.config/chiyo-cli/config.toml` for shared configuration.

## External Actions

Some commands use macOS `open` to launch URLs, files, directories, or
applications. Review generated config and selected candidates when adding custom
engines, aliases, or search roots.

## Reporting

If you find a security issue, please open a private report if GitHub security
advisories are enabled for the repository. Otherwise, open an issue with enough
detail to reproduce the behavior while avoiding sensitive local paths or data.
