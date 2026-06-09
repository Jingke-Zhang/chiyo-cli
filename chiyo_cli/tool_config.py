"""Config helpers for the user-tool framework."""

import copy
import os

from chiyo_cli.config import (
    CONFIG_PATH,
    format_module_config,
    init_module_config,
    load_config_file,
    load_module_config,
)


TOOLS_CONFIG_PATH = "~/.config/chiyo-cli/tools.toml"
CHIYO_CONFIG_MODULE = "chiyo"
DEFAULT_CHIYO_CONFIG = {
    "tool_dirs": ["~/.config/chiyo-cli/tools"],
    "enabled_tools": [],
    "wrapper_dir": "~/.local/bin",
    "completion_dir": "~/.local/share/zsh/site-functions",
}


def expand_path(value):
    return os.path.expanduser(value)


def expand_paths(values):
    return [expand_path(value) for value in values]


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

    return config


def init_chiyo_config(config_path=CONFIG_PATH):
    return init_module_config(
        CHIYO_CONFIG_MODULE,
        DEFAULT_CHIYO_CONFIG,
        config_path=config_path,
    )


def load_tools_config(config_path=TOOLS_CONFIG_PATH):
    return load_config_file(config_path)


def load_tool_config(tool_command, defaults, config_path=TOOLS_CONFIG_PATH, warn=None):
    return load_module_config(
        tool_command,
        defaults,
        config_path=config_path,
        warn=warn,
    )


def init_tool_config(tool_command, defaults, config_path=TOOLS_CONFIG_PATH):
    return init_module_config(
        tool_command,
        defaults,
        config_path=config_path,
    )


def format_chiyo_config():
    return format_module_config(CHIYO_CONFIG_MODULE, DEFAULT_CHIYO_CONFIG)


def default_tool_config(defaults):
    return copy.deepcopy(defaults)
