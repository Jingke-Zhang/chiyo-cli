"""Framework primitives for Chiyo search-pick-open tools."""

import argparse
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chiyo_cli.fzf import (
    Field,
    STYLE_PRIMARY,
    STYLE_SECONDARY,
    STYLE_PLAIN,
    choose_item_from,
)
from chiyo_cli.output import print_warning
from chiyo_cli.paths import absolute_path, compact_path, existing_dirs, expand_path


COMMON_FLAGS = {
    "--help",
    "--confirm",
    "--list-completions",
}


class ToolError(Exception):
    """User-facing tool execution error."""


class ToolFlagError(ToolError):
    """Raised when a user tool defines flags reserved by the framework."""


@dataclass(frozen=True)
class ShellAction:
    kind: str
    value: str = ""

    @classmethod
    def cd(cls, path):
        return cls("cd", str(path))

    @classmethod
    def open(cls, location):
        return cls("open", str(location))

    @classmethod
    def print(cls, value):
        return cls("print", str(value))

    @classmethod
    def none(cls):
        return cls("none", "")

    def render_shell(self):
        if self.kind == "none":
            return ""

        if self.kind == "cd":
            return f"cd {shlex.quote(self.value)}"

        if self.kind == "open":
            return f"open {shlex.quote(self.value)}"

        if self.kind == "print":
            return f"printf '%s\\n' {shlex.quote(self.value)}"

        raise ToolError(f"unknown shell action: {self.kind}")

    def execute(self):
        if self.kind == "none":
            return None

        if self.kind == "cd":
            raise ToolError("cd actions require `chiyo shell`.")

        if self.kind == "open":
            open_location(self.value)
            return self.value

        if self.kind == "print":
            print(self.value)
            return self.value

        raise ToolError(f"unknown shell action: {self.kind}")


def tool_argument_flags(tool):
    parser = argparse.ArgumentParser(
        prog=tool_cmd(tool),
        add_help=False,
    )
    tool.add_arguments(parser)
    flags = []

    for action in parser._actions:
        flags.extend(action.option_strings)

    return set(flags)


def validate_tool_flags(tool):
    conflicts = sorted(COMMON_FLAGS & tool_argument_flags(tool))

    if conflicts:
        flags = ", ".join(conflicts)
        raise ToolFlagError(
            f"{tool_cmd(tool)} defines framework-reserved flag(s): {flags}"
        )


def tool_cmd(tool):
    return getattr(tool, "cmd", None) or getattr(tool, "command", None)


class PickOpenTool:
    """Base class for small search-pick-open tools.

    Subclasses own domain behavior: data loading, matching, sorting, display,
    completion labels, custom flags, and selected-item actions. The base class
    owns the common command-line and picker workflow.
    """

    name = None
    cmd = None
    command = None
    author = None
    author_id = None
    description = None
    prompt = None
    docs = ""
    default_config = {}
    search_display_fields = [1]

    def items(self, config):
        raise NotImplementedError

    def match(self, item: Any, query: str, config: dict) -> bool:
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

    def fail(self, message, exit_code=1):
        print(f"{tool_cmd(self)}: {message}", file=sys.stderr)
        raise SystemExit(exit_code)

    def warn(self, message):
        print_warning(self.command, message)

    def path(self, value):
        return Path(expand_path(value))

    def absolute_path(self, value):
        return absolute_path(value)

    def compact_path(self, value):
        return compact_path(value)

    def existing_dirs(self, paths, label="directory"):
        return existing_dirs(paths, label, self.warn, self.fail)

    def require_command(self, command):
        try:
            return require_command(command)
        except ToolError as error:
            self.fail(str(error))

    def run_command(self, command, error_message):
        try:
            return run_command(command, error_message)
        except ToolError as error:
            self.fail(str(error))

    def glob_paths(self, root, pattern):
        return sorted(self.path(root).glob(pattern))

    def field(self, value, style=STYLE_PLAIN):
        return Field(str(value), style)

    def primary(self, value):
        return self.field(value, STYLE_PRIMARY)

    def secondary(self, value):
        return self.field(value, STYLE_SECONDARY)

    def plain(self, value):
        return self.field(value, STYLE_PLAIN)

    def cd(self, path):
        return ShellAction.cd(path)

    def open(self, location):
        return ShellAction.open(location)

    def open_location(self, location):
        open_location(location)
        return location

    def open_with_app(self, location, app):
        open_with_app(location, app)
        return location

    def print(self, value):
        return ShellAction.print(value)

    def no_action(self):
        return ShellAction.none()

    def prompt_value(self, config):
        return config.get("fzf_prompt") or self.prompt or f"{tool_cmd(self)}> "

    def query_from_args(self, args):
        return " ".join(args.query)

    def parser(self):
        validate_tool_flags(self)
        parser = argparse.ArgumentParser(
            prog=tool_cmd(self),
            description=self.description,
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Always confirm the selected item in fzf.",
        )
        parser.add_argument(
            "--list-completions",
            action="store_true",
            help="Print completion candidates, one per line.",
        )
        self.add_arguments(parser)
        parser.add_argument(
            "query",
            nargs="*",
            help="Optional query terms.",
        )
        return parser

    def filtered_items(self, items, query, config):
        return [
            item
            for item in items
            if self.match(item, query, config)
        ]

    def sorted_items(self, items, config):
        decorated = [
            (self.sort_key(item, config), index, item)
            for index, item in enumerate(items)
        ]

        if all(key is None for key, _index, _item in decorated):
            return list(items)

        return [
            item
            for _key, _index, item in sorted(
                decorated,
                key=lambda entry: (
                    entry[0] is None,
                    entry[0],
                    entry[1],
                ),
            )
        ]

    def print_completions(self, config):
        for item in self.completion_items(config):
            print(self.completion_label(item, config))

    def select_item(self, items, query, args, config):
        if query and not args.confirm and len(items) == 1:
            return items[0]

        return choose_item_from(
            items,
            self.prompt_value(config),
            "an item",
            self.fail,
            display_fields=lambda item: self.display_fields(item, config),
            search_display_fields=self.search_display_fields,
        )

    def run(self, argv=None, config=None, execute_shell_actions=True):
        config = dict(self.default_config if config is None else config)
        args = self.parser().parse_args(argv if argv is not None else sys.argv[1:])

        if args.list_completions:
            self.print_completions(config)
            return None

        query = self.query_from_args(args)
        items = self.sorted_items(
            self.filtered_items(self.items(config), query, config),
            config,
        )

        if not items:
            self.fail("no items found.")

        selected = self.select_item(items, query, args, config)

        if selected is None:
            return None

        result = self.open_item(selected, args, config)

        if execute_shell_actions and isinstance(result, ShellAction):
            return result.execute()

        return result

    def open_path(self, path):
        open_location(path)


def open_location(location):
    _run_open_command([expand_path(location)], str(location))


def open_with_app(location, app):
    arguments = ["-a", str(app)]

    if location:
        arguments.append(expand_path(location))

    _run_open_command(arguments, str(location or app))


def _run_open_command(arguments, location_label):
    if shutil.which("open") is None:
        raise ToolError("macOS 'open' command is not available.")

    result = subprocess.run(
        ["open", *arguments],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        detail = result.stderr.strip() or "unknown error"
        raise ToolError(f"could not open {location_label}: {detail}")


def require_command(command):
    path = shutil.which(command)

    if path is None:
        raise ToolError(f"{command} is not installed or not in PATH.")

    return path


def run_command(command, error_message):
    require_command(command[0])
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        detail = result.stderr.strip() or "unknown error"
        raise ToolError(f"{error_message}: {detail}")

    return result


__all__ = [
    "COMMON_FLAGS",
    "Field",
    "PickOpenTool",
    "ShellAction",
    "STYLE_PLAIN",
    "STYLE_PRIMARY",
    "STYLE_SECONDARY",
    "ToolFlagError",
    "ToolError",
    "absolute_path",
    "compact_path",
    "existing_dirs",
    "expand_path",
    "open_location",
    "open_with_app",
    "require_command",
    "run_command",
    "tool_cmd",
    "tool_argument_flags",
    "validate_tool_flags",
]
