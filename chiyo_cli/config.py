"""Shared config helpers for Chiyo CLI tools."""

import ast
import copy
import json
import os
import re

from chiyo_cli.paths import expand_path

try:
    import tomllib
except ModuleNotFoundError:
    # Python 3.11+ includes tomllib. Older installs can optionally use tomli.
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        tomllib = None


CONFIG_PATH = "~/.config/chiyo-cli/config.toml"


def strip_toml_comment(line):
    # Strip comments without treating a # inside a quoted string as a comment.
    in_quote = False
    escaped = False

    for index, char in enumerate(line):
        if escaped:
            escaped = False
            continue

        if char == "\\":
            escaped = True
            continue

        if char == '"':
            in_quote = not in_quote
            continue

        if char == "#" and not in_quote:
            return line[:index]

    return line


def parse_inline_table(value):
    # The fallback parser only needs the inline table shape used by this repo:
    # {alias = "App Name"}. Full TOML parsing is delegated to tomllib/tomli.
    pairs = {}

    for quoted_key, bare_key, item in re.findall(
        r'(?:"([^"]+)"|([A-Za-z0-9_-]+))\s*=\s*("[^"]*")',
        value,
    ):
        pairs[quoted_key or bare_key] = ast.literal_eval(item)

    return pairs


def parse_toml_value(value):
    value = value.strip()

    if value.startswith("{") and value.endswith("}"):
        return parse_inline_table(value)

    try:
        return ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return value


def load_minimal_toml(path):
    # Small fallback parser for Chiyo CLI's simple config shape. It supports
    # tables, dotted tables, strings, arrays, and simple inline string maps.
    data = {}
    current_table = None

    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            line = strip_toml_comment(line).strip()

            if not line:
                continue

            if line.startswith("[") and line.endswith("]"):
                table_name = parse_table_name(line[1:-1].strip())
                table_path = table_name.split(".")
                current_table = data

                for table in table_path:
                    current_table = current_table.setdefault(table, {})

                continue

            if current_table is not None and "=" in line:
                key, value = line.split("=", 1)
                current_table[key.strip()] = parse_toml_value(value)

    return data


def load_config_file(config_path=CONFIG_PATH):
    config_path = expand_path(config_path)

    if not os.path.exists(config_path):
        return {}

    if tomllib is None:
        return load_minimal_toml(config_path)

    with open(config_path, "rb") as file:
        return tomllib.load(file)


def load_module_config(module_name, defaults, config_path=CONFIG_PATH, warn=None):
    # If a module table exists, treat it as the user's explicit configuration.
    # Defaults are only copied in for missing keys so tools keep running, and
    # callers can surface that fallback as a warning.
    data = load_config_file(config_path)
    module_config = data.get(module_name)

    if module_config is None:
        return copy.deepcopy(defaults)

    if not isinstance(module_config, dict):
        raise ValueError(f"Invalid config: [{module_name}] must be a table.")

    config = copy.deepcopy(module_config)

    for key, value in defaults.items():
        if key in config:
            continue

        if warn is not None:
            warn(f"config [{module_name}] missing {key}; using default.")

        config[key] = copy.deepcopy(value)

    return config


def toml_quote(value):
    return json.dumps(value)


def toml_key_segment(value):
    if re.fullmatch(r"[A-Za-z0-9_-]+", value):
        return value

    return toml_quote(value)


def toml_table_header(table_name):
    return ".".join(toml_key_segment(segment) for segment in table_name.split("."))


def format_toml_value(value):
    if isinstance(value, list):
        return "[" + ", ".join(format_toml_value(item) for item in value) + "]"

    return toml_quote(value)


def append_toml_table(lines, table_name, values):
    lines.append(f"[{toml_table_header(table_name)}]")
    nested_tables = []

    for key, value in values.items():
        if isinstance(value, dict):
            nested_tables.append((key, value))
            continue

        lines.append(f"{key} = {format_toml_value(value)}")

    for key, table in nested_tables:
        lines.append("")
        append_toml_table(lines, f"{table_name}.{key}", table)


def format_module_config(module_name, defaults):
    lines = []
    append_toml_table(lines, module_name, defaults)
    return "\n".join(lines) + "\n"


def is_module_header(line, module_name):
    stripped = line.strip()

    if not stripped.startswith("[") or not stripped.endswith("]"):
        return False

    table_name = parse_table_name(stripped.strip("[]").strip())
    return table_name == module_name or table_name.startswith(f"{module_name}.")


def parse_table_name(value):
    parts = []
    current = ""
    in_quote = False
    escaped = False

    for char in value:
        if escaped:
            current += char
            escaped = False
            continue

        if char == "\\" and in_quote:
            current += char
            escaped = True
            continue

        if char == '"':
            current += char
            in_quote = not in_quote
            continue

        if char == "." and not in_quote:
            parts.append(parse_table_segment(current.strip()))
            current = ""
            continue

        current += char

    if current:
        parts.append(parse_table_segment(current.strip()))

    return ".".join(parts)


def parse_table_segment(value):
    if value.startswith('"') and value.endswith('"'):
        try:
            return ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return value.strip('"')

    return value


def remove_module_config(content, module_name):
    # Preserve other modules while replacing this command's own tables.
    lines = content.splitlines()
    kept_lines = []
    skipping = False

    for line in lines:
        stripped = line.strip()
        is_table_header = stripped.startswith("[") and stripped.endswith("]")

        if is_table_header:
            skipping = is_module_header(line, module_name)

        if not skipping:
            kept_lines.append(line)

    return "\n".join(kept_lines).strip()


def init_module_config(module_name, defaults, config_path=CONFIG_PATH):
    # Legacy helper for writing one module table while preserving unrelated
    # tables in the same TOML file.
    config_path = expand_path(config_path)
    config_dir = os.path.dirname(config_path)
    os.makedirs(config_dir, exist_ok=True)

    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as file:
            existing_config = file.read()
    else:
        existing_config = ""

    remaining_config = remove_module_config(existing_config, module_name)
    module_config = format_module_config(module_name, defaults)

    if remaining_config:
        new_config = remaining_config + "\n\n" + module_config
    else:
        new_config = module_config

    with open(config_path, "w", encoding="utf-8") as file:
        file.write(new_config)

    return config_path
