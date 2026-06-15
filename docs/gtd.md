# gtd

`gtd` loads Org agenda items from Emacs, shows them in `fzf`, and opens the
selected item's source location through `emacsclient`.

```sh
chiyo run gtd
chiyo run gtd inbox
chiyo run gtd capture "read paper"
chiyo run gtd --print-elisp
chiyo config init gtd --append
chiyo install gtd
chiyo doc gtd
```

## Options

- `--print-elisp`: print the Emacs Lisp expression used to collect agenda
  items instead of running it
- `--confirm`: always confirm the selected agenda item in `fzf`
- `--list-completions`: print completion candidates

## Capture

`gtd capture TEXT...` appends a `TODO` heading to the configured inbox file
through Emacs:

```sh
chiyo run gtd capture "read paper"
```

The default inbox is `~/org/inbox.org`. Chiyo asks Emacs to create missing
parent directories, append the heading, add a `CREATED` property, and save the
file.

## Config

Default generated config:

```toml
["jingke-zhang/gtd"]
cmds = ["gtd"]
fzf_prompt = "gtd> "
emacsclient = "emacsclient"
emacsclient_open_args = ["-n"]
agenda_span = "day"
agenda_start_day = ""

["jingke-zhang/gtd".files.inbox]
name = "Inbox"
path = "~/org/inbox.org"
bare = true
```

`agenda_span` is passed to `org-agenda-span`. Use values such as `day`, `week`,
`month`, or a number of days accepted by Org. `agenda_start_day` is passed to
`org-agenda-start-day`; leave it empty to use Org's default start day.

Use `emacsclient_open_args = ["-nw"]` to open the selected item in the current
terminal instead of asking an existing GUI frame to visit it.

## Behavior

`gtd` asks Emacs to build a normal Org agenda list with `org-agenda-list`.
Chiyo then reads the agenda lines and their Org markers as JSON, presents the
items with `fzf`, and opens the selected source file with the configured
`emacsclient_open_args`. By default this is:

```sh
emacsclient -n +LINE:COLUMN FILE
```

`gtd` installs as a shell function so terminal Emacs clients can run from the
current shell instead of from a captured Python subprocess. After changing from
an older wrapper install, run `chiyo install gtd` again and reload your shell
init so the generated `gtd.zsh` function is sourced.

Chiyo does not parse Org files directly. Emacs owns agenda generation, agenda
files, todo keywords, tags, custom agenda behavior, and marker resolution.
