"""Framework primitives for Chiyo search-pick-open tools."""

import argparse
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass

from chiyo_cli.fzf import (
    Field,
    STYLE_PRIMARY,
    STYLE_SECONDARY,
    STYLE_PLAIN,
    choose_item_from,
)
from chiyo_cli.paths import expand_path


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
        prog=tool.command,
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
            f"{tool.command} defines framework-reserved flag(s): {flags}"
        )


class PickOpenTool:
    """Base class for small search-pick-open tools.

    Subclasses own domain behavior: data loading, matching, sorting, display,
    completion labels, custom flags, and selected-item actions. The base class
    owns the common command-line and picker workflow.
    """

    name = None
    command = None
    author = None
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

    def fail(self, message, exit_code=1):
        print(f"{self.command}: {message}", file=sys.stderr)
        raise SystemExit(exit_code)

    def prompt_value(self, config):
        return config.get("fzf_prompt") or self.prompt or f"{self.command}> "

    def query_from_args(self, args):
        return " ".join(args.query)

    def parser(self):
        validate_tool_flags(self)
        parser = argparse.ArgumentParser(
            prog=self.command,
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
    if shutil.which("open") is None:
        raise ToolError("macOS 'open' command is not available.")

    result = subprocess.run(
        ["open", expand_path(location)],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        detail = result.stderr.strip() or "unknown error"
        raise ToolError(f"could not open {location}: {detail}")


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
    "open_location",
    "tool_argument_flags",
    "validate_tool_flags",
]
