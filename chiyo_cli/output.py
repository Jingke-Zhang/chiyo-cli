"""Terminal output helpers shared by Chiyo CLI tools."""

import os
import sys


STYLE_YELLOW = "\033[33m"
STYLE_RESET = "\033[0m"


def use_color(stream):
    return stream.isatty() and not os.environ.get("NO_COLOR")


def style_text(value, style, stream):
    if not use_color(stream):
        return value

    return f"{style}{value}{STYLE_RESET}"


def print_warning(tool, message):
    label = style_text("warning", STYLE_YELLOW, sys.stderr)
    print(f"{tool}: {label}: {message}", file=sys.stderr)
