"""Resolve tool commands and configured aliases to tool metadata."""

from dataclasses import dataclass

from chiyo_cli.tool_config import CONFIG_PATH, TOOLS_CONFIG_PATH


class ToolCommandError(Exception):
    pass


@dataclass(frozen=True)
class CmdConfigIssue:
    tool_key: str
    cmd: str
    message: str


def enabled_tool_keys(config):
    return set(config.get("enabled_tools", []))


def configured_cmds_and_issues(tool, config_path=TOOLS_CONFIG_PATH):
    from chiyo_cli.tool_loader import COMMAND_PATTERN
    from chiyo_cli.tool_config import load_tool_config, tool_config_defaults

    config = load_tool_config(
        tool.key,
        tool_config_defaults(tool, {}),
        config_path=config_path,
    )
    cmds = config.get("cmds", [tool.cmd])
    issues = []

    if not isinstance(cmds, list):
        return [tool.cmd], [
            CmdConfigIssue(tool.key, "cmds", "cmds must be a list of command strings")
        ]

    normalized = []

    for cmd in cmds:
        if not isinstance(cmd, str) or not cmd:
            issues.append(
                CmdConfigIssue(tool.key, str(cmd), "cmd must be a non-empty string")
            )
            continue

        if not COMMAND_PATTERN.fullmatch(cmd):
            issues.append(
                CmdConfigIssue(tool.key, cmd, "cmd must match ^[a-z][a-z0-9-]*$")
            )
            continue

        if cmd not in normalized:
            normalized.append(cmd)

    return normalized or [tool.cmd], issues


def configured_cmds(tool, config_path=TOOLS_CONFIG_PATH):
    cmds, _issues = configured_cmds_and_issues(tool, config_path=config_path)
    return cmds


def configured_cmd_issues(tools, config_path=TOOLS_CONFIG_PATH):
    issues = []

    for tool in tools:
        _cmds, tool_issues = configured_cmds_and_issues(tool, config_path=config_path)
        issues.extend(tool_issues)

    return issues


def tool_command_index(tools, config, enabled_only=True, tools_config_path=TOOLS_CONFIG_PATH):
    enabled = enabled_tool_keys(config)
    index = {}
    issues = []

    for tool in tools:
        if enabled_only and tool.key not in enabled:
            continue

        cmds, tool_issues = configured_cmds_and_issues(
            tool,
            config_path=tools_config_path,
        )
        issues.extend(tool_issues)

        for cmd in cmds:
            index.setdefault(cmd, []).append(tool)

    duplicates = {
        cmd
        for cmd, owners in index.items()
        if len(owners) > 1
    }
    return index, duplicates, issues


def duplicate_cmd_message(index, duplicates):
    parts = []

    for cmd in sorted(duplicates):
        owners = ", ".join(tool.key for tool in index[cmd])
        parts.append(f"duplicate cmd {cmd}: {owners}")

    return "; ".join(parts)


def invalid_cmd_message(issues):
    parts = []

    for issue in issues:
        parts.append(f"invalid cmd for {issue.tool_key}: {issue.cmd}: {issue.message}")

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
    index, duplicates, issues = tool_command_index(
        discovery.tools,
        config,
        enabled_only=enabled_only,
        tools_config_path=tools_config_path,
    )

    if duplicates and (enabled_only or tool_command in duplicates):
        raise ToolCommandError(duplicate_cmd_message(index, duplicates))

    matches = index.get(tool_command, [])

    if issues and enabled_only:
        raise ToolCommandError(invalid_cmd_message(issues))

    if issues and matches and matches[0].key in {issue.tool_key for issue in issues}:
        raise ToolCommandError(invalid_cmd_message(issues))

    if issues and tool_command in {issue.cmd for issue in issues}:
        raise ToolCommandError(invalid_cmd_message(issues))

    if matches:
        return matches[0], config

    if "/" in tool_command:
        for tool in discovery.tools:
            if tool.key == tool_command:
                if issues and tool.key in {issue.tool_key for issue in issues}:
                    raise ToolCommandError(invalid_cmd_message(issues))

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
