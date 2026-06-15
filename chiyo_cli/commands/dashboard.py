"""Default dashboard shown when `chiyo` is run without subcommands."""


CONFIG_PATH = "~/.config/chiyo-cli/config.toml"
TOOLS_CONFIG_PATH = "~/.config/chiyo-cli/tools.toml"


def dashboard_lines():
    from chiyo_cli.tool_config import load_chiyo_config
    from chiyo_cli.tool_loader import discover_tools
    from chiyo_cli.tool_resolver import configured_cmds, enabled_tool_keys

    config = load_chiyo_config(config_path=CONFIG_PATH)
    discovery = discover_tools(config.get("tool_dirs", []), include_builtins=True)
    enabled = enabled_tool_keys(config)
    enabled_tools = [tool for tool in discovery.tools if tool.key in enabled]
    disabled_count = len([tool for tool in discovery.tools if tool.key not in enabled])

    lines = [
        "Chiyo CLI",
        "",
        "Status",
        f"  enabled tools: {len(enabled_tools)}",
        f"  disabled tools: {disabled_count}",
        f"  config: {CONFIG_PATH}",
        f"  tools: {TOOLS_CONFIG_PATH}",
        "",
        "Enabled Tools",
    ]

    if enabled_tools:
        for tool in enabled_tools:
            cmds = ", ".join(configured_cmds(tool, config_path=TOOLS_CONFIG_PATH))
            lines.append(f"  {tool.name:20} {cmds:12} {tool.description}")
    else:
        lines.append("  none")

    if discovery.errors:
        lines.append("")
        lines.append("Warnings")

        for error in discovery.errors:
            lines.append(f"  {error.path}: {error.message}")

    lines.extend(
        [
            "",
            "Manage",
            "  chiyo tool list",
            "  chiyo doctor",
            "  chiyo config init --all --append",
            "  chiyo install TOOLS...",
            "  chiyo doc TOOL",
        ]
    )

    return lines


def dashboard():
    print("\n".join(dashboard_lines()))
