# agd

`agd` loads Org agenda items from Emacs, shows them in `fzf`, and opens the
selected item's source location through `emacsclient`.

```sh
chiyo run agd
chiyo run agd inbox
chiyo run agd capture "read paper"
chiyo run agd open inbox
chiyo run agd view todo
chiyo run agd --print-elisp
chiyo config init agd --append
chiyo install agd
chiyo doc agd
```

## Options

- `--print-elisp`: print the Emacs Lisp expression used to collect agenda
  items instead of running it
- `--confirm`: always confirm the selected agenda item in `fzf`
- `--list-completions`: print completion candidates

## Capture

`agd capture TEXT...` appends a `TODO` heading to the configured inbox file
through Emacs:

```sh
chiyo run agd capture "read paper"
```

The default inbox is `~/org/inbox.org`. Chiyo asks Emacs to create missing
parent directories, append the heading, add a `CREATED` property, and save the
file.

## Files

Configured files can be opened by alias:

```sh
chiyo run agd open inbox
```

Each file can opt into bare alias handling with `bare = true`. The default
`inbox` file enables this, so `chiyo run agd inbox` opens the inbox file. Files
with `bare = false` remain available through `agd open ALIAS` without taking
over default agenda searches.

## Views

`agd view NAME [QUERY...]` asks Emacs to build a configured agenda-like view,
then shows that view's Org marker rows in `fzf`:

```sh
chiyo run agd view todo
chiyo run agd view next email
```

Views can call an Org agenda dispatcher key:

```toml
["jingke-zhang/agenda".views.todo]
name = "Todo List"
key = "t"
```

They can also call a named Emacs function:

```toml
["jingke-zhang/agenda".views.next]
name = "Next Actions"
function = "my/agd-next-actions"
```

The function should create or switch to an agenda-like buffer whose rows carry
`org-marker` or `org-hd-marker` text properties. Chiyo reads those markers and
opens the selected source location.

## Config

Default generated config:

```toml
["jingke-zhang/agenda"]
cmds = ["agd"]
fzf_prompt = "agd> "
emacsclient = "emacsclient"
emacsclient_timeout = 30
emacsclient_open_args = ["-n"]
agenda_span = "day"
agenda_start_day = ""
default_view = "agenda"

["jingke-zhang/agenda".views.agenda]
name = "Agenda"
key = "a"

["jingke-zhang/agenda".views.todo]
name = "Todo List"
key = "t"

["jingke-zhang/agenda".files.inbox]
name = "Inbox"
path = "~/org/inbox.org"
bare = true
```

`agenda_span` is passed to `org-agenda-span`. Use values such as `day`, `week`,
`month`, or a number of days accepted by Org. `agenda_start_day` is passed to
`org-agenda-start-day`; leave it empty to use Org's default start day.
`emacsclient_timeout` limits how long Chiyo waits for Emacs to generate agenda
JSON before reporting a timeout.

Use `emacsclient_open_args = ["-nw"]` to open the selected item in the current
terminal instead of asking an existing GUI frame to visit it. This mode works
best through the installed shell function (`chiyo install agd`); if a direct
`chiyo run agd` call appears to hang, use `["-n"]` or run the `agd` shell
function from an interactive terminal.

## Behavior

`agd` asks Emacs to build a normal Org agenda list with `org-agenda-list`.
Chiyo then reads the agenda lines and their Org markers as JSON, presents the
items with `fzf`, and opens the selected source file with the configured
`emacsclient_open_args`. By default this is:

```sh
emacsclient -n +LINE:COLUMN FILE
```

`agd` installs as a shell function so terminal Emacs clients can run from the
current shell instead of from a captured Python subprocess. After changing from
an older wrapper install, run `chiyo install agd` again and reload your shell
init so the generated `agd.zsh` function is sourced.

Chiyo does not parse Org files directly. Emacs owns agenda generation, agenda
files, todo keywords, tags, custom agenda behavior, and marker resolution.
