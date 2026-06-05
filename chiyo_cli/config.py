"""Shared config helpers for Chiyo CLI tools."""

import ast
import copy
import json
import os
import re

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
                table_path = line[1:-1].strip().split(".")
                current_table = data

                for table in table_path:
                    current_table = current_table.setdefault(table, {})

                continue

            if current_table is not None and "=" in line:
                key, value = line.split("=", 1)
                current_table[key.strip()] = parse_toml_value(value)

    return data


def load_config_file(config_path=CONFIG_PATH):
    config_path = os.path.expanduser(config_path)

    if not os.path.exists(config_path):
        return {}

    if tomllib is None:
        return load_minimal_toml(config_path)

    with open(config_path, "rb") as file:
        return tomllib.load(file)


def load_module_config(module_name, defaults, config_path=CONFIG_PATH):
    # config.toml is optional. Missing values fall back to command defaults.
    config = copy.deepcopy(defaults)
    data = load_config_file(config_path)
    module_config = data.get(module_name, {})

    if not isinstance(module_config, dict):
        raise ValueError(f"Invalid config: [{module_name}] must be a table.")

    config.update(module_config)
    return config


def toml_quote(value):
    return json.dumps(value)


def format_toml_value(value):
    if isinstance(value, list):
        return "[" + ", ".join(format_toml_value(item) for item in value) + "]"

    return toml_quote(value)


def format_module_config(module_name, defaults):
    # Shared init only renders flat keys. Tools with nested tables, such as ws,
    # provide their own renderer and still reuse remove_module_config.
    lines = [f"[{module_name}]"]

    for key, value in defaults.items():
        if isinstance(value, dict):
            continue

        lines.append(f"{key} = {format_toml_value(value)}")

    return "\n".join(lines) + "\n"


def is_module_header(line, module_name):
    stripped = line.strip()

    if not stripped.startswith("[") or not stripped.endswith("]"):
        return False

    table_name = stripped.strip("[]").strip()
    return table_name == module_name or table_name.startswith(f"{module_name}.")


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
    # --config-init writes only this command's module so the shared config file
    # can also hold settings for other Chiyo CLI commands.
    config_path = os.path.expanduser(config_path)
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
