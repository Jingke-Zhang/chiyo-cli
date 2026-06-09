"""Shared fzf display and selection helpers.

Chiyo tools usually follow the same interaction shape:

1. Collect candidate objects.
2. Render each candidate as one or more human-readable display fields.
3. Let fzf search a separate, intentionally chosen set of filter fields.
4. Map the selected row back to the original candidate object.

The important abstraction is that display text and filter text are separate
interfaces. A path or URL can be shown to disambiguate a row without making it
searchable, while aliases or normalized names can be searchable without taking
over the visible layout.
"""

import shutil
import subprocess
import unicodedata
from dataclasses import dataclass


STYLE_RESET = "\033[0m"
STYLE_PRIMARY = "\033[1;32m"
STYLE_SECONDARY = "\033[3;4m"
STYLE_PLAIN = ""
STYLE_CONCEAL = "\033[8m"
COLUMN_GAP = 2


@dataclass
class Field:
    """One visible fzf cell.

    ``value`` is the text shown to the user. ``style`` may contain ANSI escape
    codes from this module or a tool-specific palette. Search text should be
    passed separately through ``filter_rows`` instead of embedding hidden text
    in the visible value.
    """

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


def normalize_filter_row(filter_row):
    """Return plain text fields used only for fzf filtering.

    Filter rows accept plain strings for the common case and ``Field`` objects
    when a caller wants to reuse a display field value directly.
    """

    return [
        field.value if isinstance(field, Field) else str(field)
        for field in filter_row
    ]


def conceal_text(value):
    """Hide filter text from the terminal while keeping it searchable by fzf.

    fzf applies ``--nth`` after ``--with-nth`` on recent versions, so columns
    omitted from ``--with-nth`` are not searchable. Concealed ANSI fields let us
    keep filter text in fzf's transformed line without showing it to the user.
    """

    return style_text(value, STYLE_CONCEAL)


def format_row(index, fields, widths, filter_fields=None):
    """Format one fzf input line.

    The line layout is:

    ``visible display fields`` + optional ``hidden filter fields`` + ``#index``

    fzf receives every tab-delimited field, but ``--with-nth`` shows only the
    display fields. The final stable index is never shown or searched; it maps
    the selected fzf row back to the original item even when display text is not
    unique.
    """

    cells = []

    for field_index, field in enumerate(fields):
        padding = ""

        if field_index < len(fields) - 1:
            padding_width = (
                widths[field_index] - display_width(field.value) + COLUMN_GAP
            )
            padding = " " * padding_width

        cells.append(style_text(field.value, field.style) + padding)

    if filter_fields is not None:
        cells.extend(
            conceal_text(value)
            for value in normalize_filter_row(filter_fields)
        )

    return "\t".join(cells) + f"\t#{index}"


def format_rows(rows, filter_rows=None):
    """Format all fzf input rows.

    ``rows`` is the display interface: a list of lists of ``Field`` objects.
    ``filter_rows`` is the filter interface: a parallel list of plain strings
    that fzf should search. When ``filter_rows`` is omitted, fzf searches the
    visible display fields.
    """

    if filter_rows is not None and len(filter_rows) != len(rows):
        raise ValueError("filter_rows must have the same length as rows.")

    widths = field_widths(rows)
    return [
        format_row(
            index,
            fields,
            widths,
            None if filter_rows is None else filter_rows[index],
        )
        for index, fields in enumerate(rows)
    ]


def field_range(count, start=1):
    return ",".join(str(index) for index in range(start, start + count))


def filter_field_numbers(visible_field_count, filter_rows):
    if filter_rows is None:
        return field_range(visible_field_count)

    filter_field_count = max((len(row) for row in filter_rows), default=0)
    return field_range(filter_field_count, visible_field_count + 1)


def display_field_numbers(visible_field_count, filter_rows):
    if filter_rows is None:
        return field_range(visible_field_count)

    filter_field_count = max((len(row) for row in filter_rows), default=0)
    return field_range(visible_field_count + filter_field_count)


def choose_item(
    items,
    rows,
    prompt,
    error_label,
    fail,
    search_field_numbers=None,
    filter_rows=None,
):
    """Return the selected item using fzf.

    ``rows`` defines the display row for each item. ``filter_rows`` optionally
    defines a separate search row for each item; these fields are hidden from
    the user but used by fzf's ``--nth``. New tools should prefer
    ``filter_rows`` over ``search_field_numbers`` because it is independent of
    display column order.

    ``search_field_numbers`` remains for older callers that want fzf to search
    selected visible columns. It cannot be combined with ``filter_rows``.
    """

    if search_field_numbers is not None and filter_rows is not None:
        raise ValueError("Use either search_field_numbers or filter_rows, not both.")

    # fzf sees the hidden tab-delimited index, but --with-nth shows only the
    # formatted display columns to the user.
    if shutil.which("fzf") is None:
        fail("fzf is not installed or not in PATH.")

    visible_field_count = len(rows[0]) if rows else 0
    visible_fields = display_field_numbers(visible_field_count, filter_rows)
    search_fields = filter_field_numbers(visible_field_count, filter_rows)

    if search_field_numbers is not None:
        search_fields = ",".join(str(number) for number in search_field_numbers)

    command = [
        "fzf",
        f"--prompt={prompt}",
        "--ansi",
        f"--with-nth={visible_fields}",
        f"--nth={search_fields}",
        "--delimiter=\t",
    ]

    result = subprocess.run(
        command,
        input="\n".join(format_rows(rows, filter_rows)),
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
