"""Config helpers for the user-tool framework."""

import copy
from chiyo_cli.config import (
    CONFIG_PATH,
    format_module_config,
    init_module_config,
    load_config_file,
    load_module_config,
)
from chiyo_cli.paths import expand_path, expand_paths


TOOLS_CONFIG_PATH = "~/.config/chiyo-cli/tools.toml"
CHIYO_CONFIG_MODULE = "chiyo"
DEFAULT_CHIYO_CONFIG = {
    "tool_dirs": ["~/.config/chiyo-cli/tools"],
    "enabled_tools": [
        "jingke-zhang/go-or-pick",
        "jingke-zhang/web-search",
        "jingke-zhang/workspace",
    ],
    "wrapper_dir": "~/.local/bin",
    "completion_dir": "~/.local/share/zsh/site-functions",
    "shell_dir": "~/.local/share/chiyo-cli/shell",
}


def load_chiyo_config(config_path=CONFIG_PATH, warn=None):
    config = load_module_config(
        CHIYO_CONFIG_MODULE,
        DEFAULT_CHIYO_CONFIG,
        config_path=config_path,
        warn=warn,
    )

    config["tool_dirs"] = expand_paths(config["tool_dirs"])
    config["wrapper_dir"] = expand_path(config["wrapper_dir"])
    config["completion_dir"] = expand_path(config["completion_dir"])
    config["shell_dir"] = expand_path(config["shell_dir"])

    return config


def load_raw_chiyo_config(config_path=CONFIG_PATH, warn=None):
    return load_module_config(
        CHIYO_CONFIG_MODULE,
        DEFAULT_CHIYO_CONFIG,
        config_path=config_path,
        warn=warn,
    )


def init_chiyo_config(config_path=CONFIG_PATH):
    return init_module_config(
        CHIYO_CONFIG_MODULE,
        DEFAULT_CHIYO_CONFIG,
        config_path=config_path,
    )


def load_tools_config(config_path=TOOLS_CONFIG_PATH):
    return load_config_file(config_path)


def tool_config_defaults(metadata_or_command, defaults):
    defaults = copy.deepcopy(defaults)

    if hasattr(metadata_or_command, "cmd"):
        defaults.setdefault("cmds", [metadata_or_command.cmd])

    return defaults


def load_tool_config(tool_key, defaults, config_path=TOOLS_CONFIG_PATH, warn=None):
    return load_module_config(
        tool_key,
        defaults,
        config_path=config_path,
        warn=warn,
    )


def init_tool_config(tool_key, defaults, config_path=TOOLS_CONFIG_PATH):
    return init_module_config(
        tool_key,
        defaults,
        config_path=config_path,
    )


def format_chiyo_config():
    return format_module_config(CHIYO_CONFIG_MODULE, DEFAULT_CHIYO_CONFIG)


def default_tool_config(defaults):
    return copy.deepcopy(defaults)


def normalize_enabled_tools(tools):
    seen = set()
    normalized = []

    for tool in tools:
        if not tool or tool in seen:
            continue

        seen.add(tool)
        normalized.append(tool)

    return normalized


def write_chiyo_config(config, config_path=CONFIG_PATH):
    return init_module_config(
        CHIYO_CONFIG_MODULE,
        config,
        config_path=config_path,
    )


def enable_tool(tool_command, config_path=CONFIG_PATH):
    config = load_raw_chiyo_config(config_path=config_path)
    enabled_tools = normalize_enabled_tools(config.get("enabled_tools", []))

    if tool_command not in enabled_tools:
        enabled_tools.append(tool_command)

    config["enabled_tools"] = enabled_tools
    write_chiyo_config(config, config_path=config_path)
    return tool_command in enabled_tools


def disable_tool(tool_command, config_path=CONFIG_PATH):
    config = load_raw_chiyo_config(config_path=config_path)
    enabled_tools = normalize_enabled_tools(config.get("enabled_tools", []))
    was_enabled = tool_command in enabled_tools
    config["enabled_tools"] = [
        tool
        for tool in enabled_tools
        if tool != tool_command
    ]
    write_chiyo_config(config, config_path=config_path)
    return was_enabled
