"""Shared fzf display and selection helpers."""

import shutil
import subprocess
import unicodedata
from dataclasses import dataclass


STYLE_RESET = "\033[0m"
STYLE_PRIMARY = "\033[1;32m"
STYLE_SECONDARY = "\033[3;4m"
STYLE_PLAIN = ""
COLUMN_GAP = 2


@dataclass
class Field:
    value: str
    style: str = STYLE_PLAIN


def style_text(value, style):
    if not style:
        return value

    return f"{style}{value}{STYLE_RESET}"


def display_width(value):
    # fzf aligns by terminal cells, not Python string length. East Asian wide
    # characters occupy two cells, while combining marks occupy none.
    width = 0

    for char in value:
        if unicodedata.combining(char):
            continue

        if unicodedata.east_asian_width(char) in ("F", "W"):
            width += 2
        else:
            width += 1

    return width


def field_widths(rows):
    widths = []

    for row in rows:
        for index, field in enumerate(row):
            if index == len(widths):
                widths.append(0)

            widths[index] = max(widths[index], display_width(field.value))

    return widths


def format_row(index, fields, widths):
    cells = []

    for field_index, field in enumerate(fields):
        padding = ""

        if field_index < len(fields) - 1:
            padding_width = (
                widths[field_index] - display_width(field.value) + COLUMN_GAP
            )
            padding = " " * padding_width

        cells.append(style_text(field.value, field.style) + padding)

    # Keep the stable item index outside the visible fzf columns. The caller can
    # style and align display text freely while selection still maps back to the
    # original object.
    return "".join(cells) + f"\t#{index}"


def format_rows(rows):
    widths = field_widths(rows)
    return [
        format_row(index, fields, widths)
        for index, fields in enumerate(rows)
    ]


def choose_item(items, rows, prompt, error_label, fail):
    # fzf sees the hidden tab-delimited index, but --with-nth shows only the
    # formatted display columns to the user.
    if shutil.which("fzf") is None:
        fail("fzf is not installed or not in PATH.")

    result = subprocess.run(
        [
            "fzf",
            f"--prompt={prompt}",
            "--ansi",
            "--with-nth=1",
            "--delimiter=\t",
        ],
        input="\n".join(format_rows(rows)),
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode == 130:
        return None

    if result.returncode != 0:
        fail(f"fzf failed while selecting {error_label}.")

    selected = result.stdout.strip()

    if not selected:
        return None

    index = int(selected.rsplit("#", 1)[1])
    return items[index]
