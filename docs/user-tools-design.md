# User Tool Framework Architecture

This document describes the user-tool framework that turns Chiyo CLI from a
collection of search-oriented scripts into a small, extensible search-pick-open
toolkit.

The goal is not to build a large plugin system. The goal is to make the common
shape of Chiyo tools easy to reuse:

```text
load data -> filter/sort in Python -> render rows -> pick in fzf -> act on item
```

Existing tools such as `app`, `bm`, `proj`, `gop`, `ws`, and `zo` are built-in
examples of the same interface that user-defined tools use.

## Goals

- Let users define small custom tools without copying a full command-line
  script.
- Keep user tools as single Python files when possible.
- Let Python control data loading, filtering, sorting, display content, display
  style, completion data, command-line flags, and selected-item actions.
- Treat `fzf` mostly as an interactive terminal picker, not as the main business
  logic engine.
- Provide shared installation, wrapper generation, shell completion, config,
  docs, and diagnostics.
- Make built-in tools and user tools feel consistent.
- Keep the framework lightweight enough that users can understand and audit
  their own tools.

## Non-Goals

- Do not turn Chiyo into a general package manager.
- Do not hide that user tools are arbitrary Python code.
- Do not require a complex project structure for simple tools.
- Do not force all existing tools to migrate at once.
- Do not replace `fzf`; the framework should prepare rows for `fzf`, then let
  `fzf` handle terminal selection.

## Core Motivation

Without a framework, a user can still write a small command-line tool. The
framework is valuable because it removes repeated infrastructure work:

- config loading and defaults
- `fzf` formatting, ANSI styling, width alignment, and stable selection mapping
- zsh completion generation
- executable wrapper installation
- `--confirm`, `--list-completions`, and common print/open options
- docs lookup
- doctor/install checks
- shell-sensitive actions such as `cd`
- consistent error handling

The intended result is that many tools can shrink from hundreds of lines to a
small class that only describes the domain-specific behavior.

## User Tool Location

User-defined tools should live in:

```text
~/.config/chiyo-cli/tools/
```

Example:

```text
~/.config/chiyo-cli/tools/paper.py
~/.config/chiyo-cli/tools/note.py
~/.config/chiyo-cli/tools/course.py
~/.config/chiyo-cli/tools/zotero/tool.py
```

This directory contains executable behavior, not plain configuration. Tool
files are Python code and must be treated as trusted code.

Small tools can stay as a single file. Larger tools can use a directory with a
`tool.py` entrypoint and helper modules next to it:

```text
~/.config/chiyo-cli/tools/zotero/
  tool.py
  local_api.py
  sqlite_source.py
  item.py
```

`tool.py` is loaded as a package module, so it can use relative imports such as
`from .sqlite_source import load_items`.

## Tool Definition Shape

Tools are class-based.

Reasoning:

- A class naturally groups metadata, docs, default config, flags, helper
  methods, display logic, and actions.
- Supporting only one entrypoint shape keeps loading and documentation simpler.
- A class can still be very small for simple tools.
- A class leaves room for inheritance, mixins, and specialized base classes.

The recommended pattern is one public `Tool` class per entrypoint:

```python
from chiyo_cli.toolkit import Field, PickOpenTool, STYLE_PRIMARY, STYLE_SECONDARY


class Tool(PickOpenTool):
    name = "Paper Search"
    cmd = "paper"
    author = "jingke"
    author_id = "jingke"
    description = "Search local papers and open PDFs."
    prompt = "paper> "
    docs = """
    Search papers and open local PDFs.
    """
    default_config = {
        "root": "~/Papers",
    }

    def items(self, config):
        return load_papers(config["root"])

    def match(self, item, query, config):
        return query.lower() in item["title"].lower()

    def sort_key(self, item, config):
        return (item["title"].lower(), -int(item.get("year") or 0))

    def display_fields(self, item, config):
        return [
            Field(item["title"], STYLE_PRIMARY),
            Field(item.get("authors", ""), STYLE_SECONDARY),
            Field(str(item.get("year", ""))),
        ]

    def open_item(self, item, args, config):
        self.open_path(item["pdf"])
```

## Base Class Responsibilities

The base class is `PickOpenTool`.

It provides default behavior for the common search-pick-open workflow:

```python
class PickOpenTool:
    name = None
    author = None
    author_id = None
    cmd = None
    description = None
    prompt = None
    docs = ""
    default_config = {}
    search_display_fields = [1]

    def items(self, config):
        raise NotImplementedError

    def match(self, item, query, config):
        return True

    def sort_key(self, item, config):
        return None

    def display_fields(self, item, config):
        raise NotImplementedError

    def completion_items(self, config):
        return self.items(config)

    def completion_label(self, item, config):
        return str(item)

    def add_arguments(self, parser):
        pass

    def open_item(self, item, args, config):
        raise NotImplementedError
```

The base runner handles:

- argument parsing
- config loading
- direct-open for one result when allowed
- `--confirm`
- `--list-completions`
- selection through `choose_item_from`
- invoking `open_item`
- standardized errors

The loader validates required metadata:

- `name`
- `author`
- `author_id`
- `cmd`
- `description`
- `docs`

Before installation, discovery views show compact metadata:

- `name`
- `author`
- `author_id/cmd`
- configured `cmds`
- `description`

Full docs are hidden by default and shown only when requested, for
example with a docs flag or `chiyo doc TOOL`.

`description` is concise. The enforced limit is 80 characters, which
keeps tool lists readable in normal terminal widths.

Recommended optional metadata:

- `version`
- `homepage`
- `license`

## Python-First Processing

The framework should prefer Python-side data processing.

The intended flow:

```text
items = tool.items(config)
items = [item for item in items if tool.match(item, query, config)]
items = sorted(items, key=lambda item: tool.sort_key(item, config))
rows = [tool.display_fields(item, config) for item in items]
selected = choose_item_from(items, rows)
tool.open_item(selected, args, config)
```

This lets tools use hidden data for filtering and sorting without adding hidden
columns to `fzf`.

Example:

```python
def sort_key(self, item, config):
    return (
        item["title"].lower(),
        -item.get("citation_count", 0),
    )
```

The citation count does not need to be displayed or passed to `fzf`; it is only
a Python sorting key.

## fzf Role

`fzf` should be treated as an interactive terminal picker.

It should receive:

- already-filtered items
- already-sorted items
- already-rendered rows
- selected visible columns to search

It should not be responsible for domain-specific sorting or business logic.

Interactive typing inside `fzf` can still use `fzf --nth` on selected visible
columns. Fully dynamic Python-side interactive filtering could be explored later
with `fzf --disabled` and reload bindings, but that should not be part of the
first version.

## Display Styling

The framework should keep `Field` as the primary display primitive.

Example for `app` alias display:

```python
def display_fields(self, item, config):
    alias = self.alias_for_app(item["name"], config["alias"])

    if alias:
        name_style = STYLE_PLAIN
        alias_style = STYLE_PRIMARY
    else:
        name_style = STYLE_PRIMARY
        alias_style = STYLE_PLAIN

    return [
        Field(item["name"], name_style),
        Field(alias, alias_style),
        Field(item["path"], STYLE_SECONDARY),
    ]
```

This keeps styling logic in Python, where it can depend on arbitrary item state.

## Tool Commands

An earlier possible command shape was:

```sh
chiyo paper convex optimization
chiyo zo linear algebra
chiyo app browser
```

This shape is not used. The framework avoids dynamic `chiyo TOOL ...`
dispatch. Instead, `chiyo` remains the macro-level command for configuration,
installation, documentation, diagnostics, and tool selection.

The explicit execution entrypoint is:

```sh
chiyo run paper convex optimization
chiyo run zo linear algebra
chiyo run app browser
```

If `chiyo` is called with no arguments, a future version may open an `fzf`
picker for enabled tools:

```sh
chiyo
```

This should behave like `chiyo run` with no tool name: show enabled tools in
`fzf`, let the user select one, then prompt for or pass through query text.
After selection, Chiyo should execute the selected tool directly. Most Chiyo
tools are small and local, so an extra confirmation step is unnecessary.

This keeps tool execution under one namespace and avoids conflicts between tool
names and Chiyo management commands.

## Installation Model

There are two concepts:

- enabling a tool for `chiyo run paper`
- installing a wrapper for direct `paper`

The minimum behavior should be:

```sh
chiyo run paper query
```

The recommended installed behavior should be:

```sh
chiyo install paper
paper query
```

`chiyo install paper` should generate a wrapper, but it should not
automatically enable the tool. If the tool is not enabled, installation should
warn clearly and suggest the enable command. This keeps enablement as an
explicit user decision.

`chiyo install` should be able to install any discoverable tool, including a
disabled tool. Disabled status should not block wrapper generation. The warning
should be simple:

```text
warn    fixture/paper installed but disabled for chiyo run
todo    add "fixture/paper" to [chiyo].enabled_tools in ~/.config/chiyo-cli/config.toml
```

### Wrapper vs Symlink

For user tools, generated wrappers are preferred over symlinking Python source
files.

Wrapper example:

```sh
#!/bin/sh
exec chiyo run paper "$@"
```

Installed at:

```text
~/.local/bin/paper
```

Advantages of wrappers:

- user tool files do not need a shebang
- user tool files do not need executable permissions
- Chiyo controls loading, config, error handling, and dispatch
- moving framework internals does not require changing user scripts
- wrappers are simple and auditable

Symlinking the `.py` file is not preferred because it forces each user tool to
be a complete executable script and makes framework-managed behavior harder.

## Completion Model

Each tool class should be able to provide completion candidates:

```python
def completion_items(self, config):
    return self.items(config)

def completion_label(self, item, config):
    return item["title"]
```

For a direct wrapper command, generated zsh completion can call:

```sh
chiyo run paper --list-completions
```

Generated completion example:

```zsh
#compdef paper

local -a candidates
candidates=("${(@f)$(chiyo run paper --list-completions 2>/dev/null)}")

if (( ${#candidates} == 0 )); then
  return 0
fi

_describe 'paper' candidates
```

For `chiyo run <tool>`, shell completion should complete enabled tool commands.

## Documentation Model

User tool docs should live in the Python file, not in a separate Markdown file.
Each tool must provide `name`, `cmd`, `author`, `author_id`, `description`,
and `docs`. `cmd` is the tool's default command, while `author_id/cmd` is the
stable identity used in config. Docs should support Markdown.

Example:

```python
class Tool(PickOpenTool):
    name = "Paper Search"
    cmd = "paper"
    author = "jingke"
    author_id = "jingke"
    description = "Search local papers and open PDFs."
    docs = """
    # paper

    Search local papers and open PDFs.

    ## Examples

    paper convex optimization
    paper --print-path linear algebra
    """
```

Docs can be shown with:

```sh
chiyo doc paper
```

The first version can support docs as a Markdown string. A later version may
also allow structured doc fields or a method that generates Markdown:

```python
def docs_markdown(self, config):
    return f"""
    # {self.name}

    Root: {config["root"]}
    """
```

This keeps a community-shared tool as a single file containing code, metadata,
docs, defaults, and behavior.

Built-in tools may continue to keep separate docs during migration, but the
framework should allow built-ins to expose docs through the same interface.

## Config Files

Chiyo uses two config files:

```text
~/.config/chiyo-cli/config.toml
~/.config/chiyo-cli/tools.toml
```

### `config.toml`

`config.toml` is for Chiyo infrastructure behavior.

Example:

```toml
[chiyo]
tool_dirs = ["~/.config/chiyo-cli/tools"]
enabled_tools = ["chiyo/app", "chiyo/bm", "jingke/paper", "chiyo/zo"]
wrapper_dir = "~/.local/bin"
completion_dir = "~/.local/share/zsh/site-functions"
```

### `tools.toml`

`tools.toml` is for tool-specific settings, including built-in tools and user
tools.

Example:

```toml
["jingke/paper"]
cmds = ["paper"]
root = "~/Papers"
fzf_prompt = "paper> "

["chiyo/zo"]
cmds = ["zo"]
source = "sqlite"
zotero_data_dir = "~/Zotero"

["chiyo/app".alias]
browser = "Safari"
editor = "Emacs"
```

Built-in tool config lives in `tools.toml` as part of the framework migration.
Since this project is still early and has no broad external user base, the
implementation switches directly to the new layout instead of adding a
migration command. `config.toml` contains Chiyo infrastructure settings and
`tools.toml` contains built-in and user tool settings.

## Tool Discovery And Enablement

There are two possible states:

- discoverable: a tool file exists in a configured tool directory
- enabled: the tool identity appears in `enabled_tools`

The recommended behavior:

- A file in `~/.config/chiyo-cli/tools/paper.py` is discoverable.
- `chiyo tool list` shows discoverable tools, enabled status, `author_id/cmd`,
  configured commands, `name`, `author`, and `description`.
- `chiyo tool list --docs` may include full docs, but docs should be hidden by
  default because normal discovery should stay compact.
- `chiyo run paper` only works if `paper` is enabled.
- `chiyo install paper` installs a wrapper but does not enable `paper`.
- If a user installs a disabled tool, Chiyo should warn and suggest enabling it.
- Config controls Chiyo behavior, not whether a Python file exists.

This avoids surprising execution of arbitrary Python files just because they
exist in the tools directory.

Potential command set:

```sh
chiyo tool list
chiyo tool enable paper
chiyo tool disable paper
chiyo install paper
chiyo uninstall paper
chiyo doc paper
chiyo run paper
```

Disabled tools should not run through `chiyo run`. Since `chiyo run` is the
only official module execution path, disabled means unavailable for execution.

Tool commands have only the restrictions needed for generated wrappers, zsh
functions, and completions. The loader requires commands to match
`^[a-z][a-z0-9-]*$`.

## User Flags

Tools should be able to define their own command-line flags.

The base class should expose:

```python
def add_arguments(self, parser):
    parser.add_argument("--print-path", action="store_true")

def open_item(self, item, args, config):
    if args.print_path:
        print(item["path"])
        return

    self.open_path(item["path"])
```

This supports tools such as:

- `chiyo run bm --print-url`
- `chiyo run zo --print-path`
- `chiyo run zo --open-pdf`
- `chiyo run app --print-name`
- future custom actions

The framework should reserve common flags such as:

```text
--help
--confirm
--list-completions
```

Tool-specific flags should not conflict with reserved framework flags.

## Shell-Sensitive Tools

Tools such as `gop` and `proj` need special handling because a subprocess
cannot change the parent shell's working directory.

The framework should provide an explicit shell action interface.

This is called a shell action protocol: a structured way for a Python tool to
tell the surrounding shell what should happen after selection.

Why this is needed:

- `open file.pdf` can run inside Python because it launches an external
  application.
- `cd ~/project` cannot run inside Python if the goal is to change the user's
  current terminal directory. A child process cannot change the parent shell's
  state.
- Earlier `gop` and `proj` implementations solved this with shell functions
  that called helper commands, captured the selected path, then ran `cd` in the
  parent shell.

The framework should make this explicit instead of hiding it in tool-specific
shell scripts.

Possible shape:

```python
from chiyo_cli.toolkit import ShellAction


def selected_action(self, item, args, config):
    if item["is_dir"]:
        return ShellAction.cd(item["path"])

    return ShellAction.open(item["path"])
```

Recommended action types:

```python
ShellAction.open(path_or_url)
ShellAction.cd(path)
ShellAction.print(value)
ShellAction.none()
```

For normal wrappers, Chiyo can execute `open` or print directly. For actions
that must modify the parent shell, such as `cd`, shell integration must
interpret the result.

Older helper-command style:

```sh
target="$(chiyo gop-select "$@")"
cd "$target"
```

Current unified style:

```sh
eval "$(chiyo shell gop "$@")"
```

In this model, `chiyo shell gop "$@"` would print shell-safe code such as:

```sh
cd '/Users/me/project'
```

The shell integration would evaluate that code in the parent shell.

Serialization question explanation: Python must return the selected action to a
shell function somehow. The serialization format is the wire format between
Python and shell integration.

Recommended first version:

- For normal `chiyo run TOOL`, execute non-shell actions directly in Python.
- For parent-shell actions, expose a dedicated command such as
  `chiyo shell TOOL ...`.
- `chiyo shell` should print shell code that is already safely quoted.
- The shell function should only evaluate output from trusted Chiyo commands.

Example output:

```sh
cd '/Users/me/project'
```

This is simpler than JSON for the shell bridge because the shell ultimately
needs shell code. A JSON format can be considered later if multiple shells need
different renderers.

Recommendation:

- Keep ordinary tools on `chiyo run TOOL`.
- Add `chiyo shell TOOL ...` as the dedicated shell bridge for tools that return
  `ShellAction.cd` or another parent-shell action.
- Use `proj` as the first migration target because it is simpler than `gop`.
- Use `gop` after the protocol is proven, because it mixes directory `cd` and
  file `open`.

## Built-In Tool Status

Built-in tools use the same framework interface as user tools.

Migration order:

1. `ws`: simple data, simple action, no filesystem walking
2. `bm`: local data source, URL action
3. `app`: aliases and styled display
4. `zo`: richer data source and custom flags
5. `proj`: shell `cd` behavior
6. `gop`: streaming/search-root behavior and shell-sensitive action

The simpler tools proved the interface first, then the shell-sensitive and
larger data-source tools moved over.

## Security Model

User tools are arbitrary Python code.

Security principles:

- Loading a user tool means executing trusted code.
- Community-shared tools should be reviewed before enabling or installing.
- `chiyo tool list` may read required metadata by importing the tool file in a
  small helper process and returning `name`, `cmd`, `author`, `author_id`,
  `description`, and optionally `docs`.
- Metadata does not need a separate database. The Python file remains the source
  of truth.
- `chiyo install` should show the tool path and name before installing wrappers.
- Doctor/security docs should mention user tool execution explicitly.

Potential future improvement:

- A manifest header could expose metadata without executing the full file.

This is not required for the first version. Importing in a helper process is
simple enough and keeps single-file tools easy to write.

## Proposed Module Layout

Potential new modules:

```text
chiyo_cli/toolkit.py
chiyo_cli/tool_loader.py
chiyo_cli/tool_config.py
```

### `toolkit.py`

Exports framework primitives:

- `PickOpenTool`
- `Field`
- style constants
- open helpers
- shell action objects

### `tool_loader.py`

Responsible for:

- discovering built-in tools
- discovering user tools
- loading a `Tool` class from a Python file
- validating names and reserved words
- checking enabled tools

### `tool_config.py`

Responsible for:

- loading `config.toml`
- loading `tools.toml`
- merging tool defaults with configured values
- initializing tool config sections

## Example User Tool

```python
from pathlib import Path

from chiyo_cli.toolkit import Field, PickOpenTool, STYLE_PRIMARY, STYLE_SECONDARY


class Tool(PickOpenTool):
    name = "Paper Search"
    cmd = "paper"
    author = "jingke"
    author_id = "jingke"
    description = "Search local papers and open PDFs."
    prompt = "paper> "
    docs = """
    # paper

    Search local papers and open PDFs.
    """
    default_config = {
        "root": "~/Papers",
    }

    def items(self, config):
        root = Path(config["root"]).expanduser()
        return [
            {
                "title": path.stem,
                "path": str(path),
                "year": "",
            }
            for path in root.rglob("*.pdf")
        ]

    def match(self, item, query, config):
        if not query:
            return True

        return all(
            term in item["title"].lower()
            for term in query.lower().split()
        )

    def sort_key(self, item, config):
        return item["title"].lower()

    def display_fields(self, item, config):
        return [
            Field(item["title"], STYLE_PRIMARY),
            Field(item["path"], STYLE_SECONDARY),
        ]

    def completion_label(self, item, config):
        return item["title"]

    def add_arguments(self, parser):
        parser.add_argument("--print-path", action="store_true")

    def open_item(self, item, args, config):
        if args.print_path:
            print(item["path"])
            return

        self.open_path(item["path"])
```

## Design Status

Resolved design choices:

- `chiyo install TOOL` should not automatically enable the tool.
- `chiyo install TOOL` should still install disabled tools, but it must warn.
- Disabled-tool install warning should use this fixed format:
  `warn    TOOL installed but disabled for chiyo run` and
  `todo    add "TOOL" to [chiyo].enabled_tools in ~/.config/chiyo-cli/config.toml`.
- Installed wrappers should call `chiyo run TOOL "$@"`.
- Dynamic `chiyo TOOL ...` dispatch should not be part of the design.
- The tool config file should be named `tools.toml`.
- Built-in tool config lives in `tools.toml`.
- Disabled tools should not run through `chiyo run`.
- `chiyo` with no arguments should execute the selected tool directly after the
  tool is selected in `fzf`.
- Tool metadata must include `name`, `cmd`, `author`, `author_id`,
  `description`, and `docs`.
- Before installation, default discovery output should show only `name`,
  `author`, `author_id/cmd`, configured commands, and `description`; docs
  should require a flag or `chiyo doc TOOL`.
- `description` should be limited to 80 characters.
- Required metadata may be read by importing the tool file in a small helper
  process; no metadata database is needed.
- Tool docs should support Markdown strings, with optional generated Markdown in
  a later version. `docs_markdown(self, config)` can be deferred.
- Shell-sensitive tools should use an explicit `ShellAction` protocol.
- The shell bridge command should be `chiyo shell TOOL ...`.
- Existing config can switch directly to `tools.toml`; no migration command is
  needed at this stage.
- Parent-shell actions should serialize as safely quoted shell code in the first
  version.
- Tool commands must match `^[a-z][a-z0-9-]*$` so generated wrappers, zsh
  functions, and completions remain safe and predictable.
- Tool config sections use `author_id/cmd`. The optional `cmds` list in
  `tools.toml` defines every command alias that can run or install the tool.
- Enabled tools must not claim the same configured command. Duplicate commands
  are reported as errors and are not dispatched.
- Tool-specific flags must not conflict with common framework flags such as
  `--help`, `--confirm`, and `--list-completions`.

Remaining questions:

- No unresolved design questions at this stage. Future questions should be
  captured as implementation notes near the code they affect.

## Historical Implementation Plan

The framework was split into small steps that could each be tested and reviewed
independently. The plan below remains as historical context for why the current
modules and tests are shaped the way they are.

1. Add `PickOpenTool` and a framework runner built on `choose_item_from`.
2. Add fixture user tools for tests, such as:
   - a valid `paper.py`
   - a tool missing required metadata
   - a discoverable but disabled tool
   - a tool with conflicting flags
3. Split the config model:
   - `config.toml` for Chiyo infrastructure
   - `tools.toml` for built-in and user tool settings
4. Add metadata loading and validation:
   - required `name`
   - required `cmd`
   - required `author`
   - required `author_id`
   - required `description`
   - required `docs`
   - 80-character `description` limit
5. Add user tool discovery from `~/.config/chiyo-cli/tools`.
6. Add enable/disable support:
   - `chiyo tool enable TOOL`
   - `chiyo tool disable TOOL`
   - enabled tools stored in `[chiyo].enabled_tools` as `author_id/cmd`
7. Add `chiyo tool list`:
   - show enabled status
   - show `name`, `author`, `author_id/cmd`, configured commands, and
     `description`
   - hide docs by default
   - optionally show docs with a flag
8. Add `chiyo doc TOOL`.
9. Add explicit execution through `chiyo run TOOL ...`.
10. Add framework flag validation so user flags cannot conflict with common
    framework flags such as `--help`, `--confirm`, and `--list-completions`.
11. Add wrapper install/uninstall:
    - `chiyo install TOOL`
    - `chiyo uninstall TOOL`
    - wrappers call `chiyo run TOOL "$@"`
    - disabled installed tools emit the fixed warning format
12. Add generated zsh completion for installed wrappers.
13. Add tool doctor checks:
    - tool file exists
    - metadata is valid
    - enabled tool can be loaded
    - wrapper exists when installed
    - wrapper points to `chiyo run TOOL "$@"`
    - generated completion exists when installed
    - installed but disabled tools are reported as warnings
14. Migrate one simple built-in tool, likely `ws` or `bm`, as the first
    framework-backed built-in.
15. Migrate `app` and `zo` after the first built-in proves the interface.
16. Add `ShellAction` and `chiyo shell TOOL ...`.
17. Migrate `proj` after shell action support exists.
18. Migrate `gop` after `proj` proves the shell bridge, because `gop` mixes
    directory `cd` and file `open` behavior.

## Built-In Migration Completion Criteria

Each built-in migration should satisfy the same completion criteria:

- The legacy command still works.
- `chiyo run TOOL ...` works.
- Tool config is read from `tools.toml`.
- Tool docs can be viewed through `chiyo doc TOOL`.
- Existing shell completion still works.
- Generated wrapper completion works when installed.
- Tests cover both legacy command behavior and framework command behavior.

## Risk Controls

The framework migration should avoid breaking the existing small tools while the
new interface is being built.

Risk controls:

- Keep existing commands working at every step.
- Run the full test suite after each implementation step.
- Start with a simple built-in tool before migrating richer tools.
- Do not migrate `gop` or `proj` until shell action support is designed and
  tested.
- Keep user-tool loading tests separate from built-in migration tests.
- Treat user tools as trusted Python and document that security model clearly.
