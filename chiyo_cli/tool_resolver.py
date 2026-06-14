"""Resolve tool commands and configured aliases to tool metadata."""

from chiyo_cli.tool_config import CONFIG_PATH, TOOLS_CONFIG_PATH


class ToolCommandError(Exception):
    pass


def enabled_tool_keys(config):
    return set(config.get("enabled_tools", []))


def configured_cmds(tool, config_path=TOOLS_CONFIG_PATH):
    from chiyo_cli.tool_config import load_tool_config, tool_config_defaults

    config = load_tool_config(
        tool.key,
        tool_config_defaults(tool, {}),
        config_path=config_path,
    )
    cmds = config.get("cmds", [tool.cmd])

    if not isinstance(cmds, list):
        return [tool.cmd]

    normalized = []

    for cmd in cmds:
        if not isinstance(cmd, str) or not cmd:
            continue

        if cmd not in normalized:
            normalized.append(cmd)

    return normalized or [tool.cmd]


def tool_command_index(tools, config, enabled_only=True, tools_config_path=TOOLS_CONFIG_PATH):
    from chiyo_cli.tool_loader import COMMAND_PATTERN

    enabled = enabled_tool_keys(config)
    index = {}

    for tool in tools:
        if enabled_only and tool.key not in enabled:
            continue

        for cmd in configured_cmds(tool, config_path=tools_config_path):
            if not COMMAND_PATTERN.fullmatch(cmd):
                continue

            index.setdefault(cmd, []).append(tool)

    duplicates = {
        cmd
        for cmd, owners in index.items()
        if len(owners) > 1
    }
    return index, duplicates


def duplicate_cmd_message(index, duplicates):
    parts = []

    for cmd in sorted(duplicates):
        owners = ", ".join(tool.key for tool in index[cmd])
        parts.append(f"duplicate cmd {cmd}: {owners}")

    return "; ".join(parts)


def resolve_tool_command(
    tool_command,
    enabled_only=True,
    config_path=CONFIG_PATH,
    tools_config_path=TOOLS_CONFIG_PATH,
):
    from chiyo_cli.tool_config import load_chiyo_config
    from chiyo_cli.tool_loader import discover_tools

    config = load_chiyo_config(config_path=config_path)
    discovery = discover_tools(config.get("tool_dirs", []), include_builtins=True)
    index, duplicates = tool_command_index(
        discovery.tools,
        config,
        enabled_only=enabled_only,
        tools_config_path=tools_config_path,
    )

    if duplicates and (enabled_only or tool_command in duplicates):
        raise ToolCommandError(duplicate_cmd_message(index, duplicates))

    matches = index.get(tool_command, [])

    if matches:
        return matches[0], config

    if "/" in tool_command:
        for tool in discovery.tools:
            if tool.key == tool_command:
                if enabled_only and tool.key not in enabled_tool_keys(config):
                    break

                return tool, config

    return None


def tool_metadata_by_command(
    tool_command,
    config_path=CONFIG_PATH,
    tools_config_path=TOOLS_CONFIG_PATH,
):
    resolved = resolve_tool_command(
        tool_command,
        enabled_only=False,
        config_path=config_path,
        tools_config_path=tools_config_path,
    )
    return None if resolved is None else resolved[0]
