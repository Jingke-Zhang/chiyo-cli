"""Shared fzf display and selection helpers.

Chiyo tools usually follow the same interaction shape:

1. Collect candidate objects.
2. Let Python filter, sort, and render candidate objects.
3. Let fzf display the prepared rows and handle terminal selection.
4. Map the selected row back to the original Python object.

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
    passed separately through ``filter_rows`` when a tool needs searchable text
    that is not already visible, or selected with ``search_display_fields`` when
    a tool wants to search only some visible columns.
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


def prepare_items(items, rows=None, display_fields=None, filter_item=None, sort_key=None):
    """Return ``(items, rows)`` after Python-side filtering, sorting, and display.

    ``display_fields`` is a callable that receives an item and returns a list of
    ``Field`` objects. ``filter_item`` and ``sort_key`` operate on the original
    Python objects before rows are rendered, so callers can use data that is not
    shown to fzf without adding hidden fzf columns.
    """

    if rows is not None and display_fields is not None:
        raise ValueError("Use either rows or display_fields, not both.")

    prepared_items = list(items)

    if filter_item is not None:
        prepared_items = [item for item in prepared_items if filter_item(item)]

    if sort_key is not None:
        prepared_items = sorted(prepared_items, key=sort_key)

    if display_fields is not None:
        return prepared_items, [display_fields(item) for item in prepared_items]

    if rows is None:
        raise ValueError("rows or display_fields is required.")

    prepared_rows = list(rows)

    if filter_item is not None or sort_key is not None:
        pairs = list(zip(items, prepared_rows))

        if filter_item is not None:
            pairs = [
                (item, row)
                for item, row in pairs
                if filter_item(item)
            ]

        if sort_key is not None:
            pairs = sorted(pairs, key=lambda pair: sort_key(pair[0]))

        return [item for item, _row in pairs], [row for _item, row in pairs]

    return prepared_items, prepared_rows


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
    search_display_fields=None,
    filter_rows=None,
    display_fields=None,
    filter_item=None,
    sort_key=None,
):
    """Return the selected item using fzf.

    ``rows`` defines prebuilt display rows. ``display_fields`` can build those
    rows from each item instead. ``filter_item`` and ``sort_key`` run in Python
    before fzf sees anything.

    ``search_display_fields`` optionally limits fzf matching to selected visible
    columns using 1-based field numbers. ``filter_rows`` defines separate
    search-only fields for tools that need to match text that is not visible,
    such as absolute paths behind a compact display path.

    ``search_field_numbers`` remains for older callers that want to pass raw
    fzf field numbers. It cannot be combined with the higher-level search
    interfaces.
    """

    search_interfaces = [
        search_field_numbers is not None,
        search_display_fields is not None,
        filter_rows is not None,
    ]

    if sum(search_interfaces) > 1:
        raise ValueError(
            "Use only one of search_display_fields, search_field_numbers, or filter_rows."
        )

    if filter_rows is not None and (filter_item is not None or sort_key is not None):
        raise ValueError("filter_rows cannot be combined with filter_item or sort_key.")

    items, rows = prepare_items(
        items,
        rows=rows,
        display_fields=display_fields,
        filter_item=filter_item,
        sort_key=sort_key,
    )

    # fzf sees the hidden tab-delimited index, but --with-nth shows only the
    # formatted display columns to the user.
    if shutil.which("fzf") is None:
        fail("fzf is not installed or not in PATH.")

    visible_field_count = len(rows[0]) if rows else 0
    visible_fields = display_field_numbers(visible_field_count, filter_rows)
    search_fields = filter_field_numbers(visible_field_count, filter_rows)

    if search_field_numbers is not None:
        search_fields = ",".join(str(number) for number in search_field_numbers)

    if search_display_fields is not None:
        search_fields = ",".join(str(number) for number in search_display_fields)

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


def choose_item_from(
    items,
    prompt,
    error_label,
    fail,
    display_fields,
    search_display_fields=None,
    filter_item=None,
    sort_key=None,
):
    """Function-oriented wrapper around ``choose_item``.

    This is the preferred API when Python owns item filtering, sorting, and
    display rendering, and fzf is only the terminal picker.
    """

    return choose_item(
        items,
        None,
        prompt,
        error_label,
        fail,
        display_fields=display_fields,
        search_display_fields=search_display_fields,
        filter_item=filter_item,
        sort_key=sort_key,
    )
