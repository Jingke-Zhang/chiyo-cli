"""Explicit path normalization helpers for Chiyo tools."""

import os


def expand_path(path):
    return os.path.expanduser(str(path))


def absolute_path(path):
    return os.path.abspath(expand_path(path))


def expand_paths(paths):
    return [expand_path(path) for path in paths]


def compact_path(path):
    home = expand_path("~")

    if path == home:
        return "~"

    if str(path).startswith(home + os.sep):
        return "~" + str(path)[len(home):]

    return str(path)


def default_fail(message):
    raise RuntimeError(message)


def default_warn(_message):
    return None


def existing_dirs(paths, label, warn=None, fail=None):
    warn = warn or default_warn
    fail = fail or default_fail
    normalized = []

    for path in paths:
        expanded = absolute_path(path)

        if not os.path.isdir(expanded):
            warn(f"skipping missing {label}: {expanded}")
            continue

        normalized.append(expanded)

    if not normalized:
        fail(f"no valid {label}s found.")

    return normalized
