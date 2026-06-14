#!/usr/bin/env python3

import argparse
import os
from pathlib import Path
import shutil
import sys

from chiyo_cli.tool_resolver import ToolCommandError

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

BIN_DIR = os.path.join(REPO_ROOT, "bin")
SHELL_DIR = os.path.join(REPO_ROOT, "shell")
COMPLETIONS_DIR = os.path.join(REPO_ROOT, "completions")
CONFIG_PATH = "~/.config/chiyo-cli/config.toml"
TOOLS_CONFIG_PATH = "~/.config/chiyo-cli/tools.toml"
LOCAL_BIN_DIR = "~/.local/bin"
ZSH_SITE_FUNCTIONS_DIR = "~/.local/share/zsh/site-functions"
COMMANDS = ["chiyo"]
COMPLETIONS = []
SHELL_INTEGRATION = 'eval "$(chiyo init zsh)"'
LEGACY_SHELL_HELPERS = {
    "gop": ["gop-select"],
    "proj": ["proj-select"],
}
CHIYO_CONFIG_TARGET = "chiyo"


class ConfigInitRefused(Exception):
    pass


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Manage Chiyo CLI shell integration and diagnostics.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init",
        help="Print shell initialization code.",
    )
    init_parser.add_argument(
        "shell",
        choices=["zsh"],
        help="Shell to initialize.",
    )

    subparsers.add_parser(
        "doctor",
        help="Check local Chiyo CLI setup.",
    )

    doc_parser = subparsers.add_parser(
        "doc",
        help="Print docs for a discoverable tool.",
    )
    doc_parser.add_argument("tool", help="Tool command to document.")

    run_parser = subparsers.add_parser(
        "run",
        help="Run an enabled user tool.",
    )
    run_parser.add_argument("tool", help="Enabled tool command to run.")
    run_parser.add_argument(
        "tool_args",
        nargs=argparse.REMAINDER,
        help="Arguments forwarded to the selected tool.",
    )

    shell_parser = subparsers.add_parser(
        "shell",
        help="Print shell code for a shell-action tool.",
    )
    shell_parser.add_argument("tool", help="Enabled tool command to run.")
    shell_parser.add_argument(
        "tool_args",
        nargs=argparse.REMAINDER,
        help="Arguments forwarded to the selected tool.",
    )

    install_parser = subparsers.add_parser(
        "install",
        help="Install a direct wrapper for a discoverable tool.",
    )
    install_parser.add_argument(
        "tools",
        nargs="+",
        metavar="TOOL",
        help="Tool commands to install.",
    )

    uninstall_parser = subparsers.add_parser(
        "uninstall",
        help="Uninstall a direct wrapper for a discoverable tool.",
    )
    uninstall_parser.add_argument(
        "tools",
        nargs="+",
        metavar="TOOL",
        help="Tool commands to uninstall.",
    )

    config_parser = subparsers.add_parser(
        "config",
        help="Manage Chiyo CLI config.",
    )
    config_subparsers = config_parser.add_subparsers(
        dest="config_command",
        required=True,
    )
    config_init_parser = config_subparsers.add_parser(
        "init",
        help="Write default config for selected tools.",
    )
    config_init_parser.add_argument(
        "tools",
        nargs="*",
        help="Tool config sections to initialize.",
    )
    config_init_parser.add_argument(
        "--all",
        action="store_true",
        help="Initialize every tool config section.",
    )
    config_mode = config_init_parser.add_mutually_exclusive_group()
    config_mode.add_argument(
        "--write",
        action="store_const",
        const="write",
        dest="config_mode",
        help="Write only when the config file is missing or empty. Default.",
    )
    config_mode.add_argument(
        "--append",
        action="store_const",
        const="append",
        dest="config_mode",
        help="Append missing tool sections without replacing existing ones.",
    )
    config_mode.add_argument(
        "--force",
        action="store_const",
        const="force",
        dest="config_mode",
        help="Replace selected tool sections.",
    )
    config_init_parser.set_defaults(config_mode="write")

    tool_parser = subparsers.add_parser(
        "tool",
        help="Manage Chiyo user-tool framework state.",
    )
    tool_subparsers = tool_parser.add_subparsers(
        dest="tool_command",
        required=True,
    )
    tool_list_parser = tool_subparsers.add_parser(
        "list",
        help="List discoverable user tools.",
    )
    tool_list_parser.add_argument(
        "--docs",
        action="store_true",
        help="Include tool docs in the listing.",
    )
    tool_enable_parser = tool_subparsers.add_parser(
        "enable",
        help="Enable a tool command for chiyo run.",
    )
    tool_enable_parser.add_argument("tool", help="Tool command to enable.")
    tool_disable_parser = tool_subparsers.add_parser(
        "disable",
        help="Disable a tool command for chiyo run.",
    )
    tool_disable_parser.add_argument("tool", help="Tool command to disable.")

    return parser.parse_args(argv)


def init_zsh():
    # Print shell code instead of editing dotfiles directly; callers can review
    # it, append it, or embed it in their own shell management setup.
    config = chiyo_config()
    completions_dir = os.path.expanduser(config["completion_dir"])
    shell_dir = os.path.expanduser(config["shell_dir"])
    return "\n".join(
        [
            "# Chiyo CLI",
            "# Config: run `chiyo config init --all --append` once for explicit defaults.",
            f'fpath=("{completions_dir}" $fpath)',
            "autoload -Uz compinit",
            "compinit",
            f'for chiyo_shell_file in "{shell_dir}"/*.zsh; do',
            '  [ -r "$chiyo_shell_file" ] && source "$chiyo_shell_file"',
            "done",
            "unset chiyo_shell_file",
            "",
        ]
    )


def print_init(shell):
    if shell == "zsh":
        print(init_zsh())
        return

    raise ValueError(f"Unsupported shell: {shell}")


def check_command(name):
    path = shutil.which(name)

    if path:
        return "ok", path

    return "missing", "not found"


def check_file(path):
    expanded = os.path.expanduser(path)

    if os.path.exists(expanded):
        return "ok", expanded

    return "missing", "not found"


def check_symlink(label, target, expected_source):
    target = os.path.expanduser(target)

    if not os.path.lexists(target):
        return "missing", f"{target} not found", label

    if not os.path.islink(target):
        return "warn", f"{target} exists but is not a symlink", label

    current = os.readlink(target)

    if current != expected_source:
        return "warn", f"{target} -> {current}; expected {expected_source}", label

    return "ok", f"{target} -> {expected_source}", label


def check_path_contains(path):
    expanded = os.path.expanduser(path)

    if expanded in os.environ.get("PATH", "").split(os.pathsep):
        return "ok", f"{expanded} is in PATH", "PATH"

    return "todo", f"add {path} to PATH", "PATH"


def zshrc_path():
    zdotdir = os.environ.get("ZDOTDIR")

    if zdotdir:
        return os.path.join(os.path.expanduser(zdotdir), ".zshrc")

    return os.path.expanduser("~/.zshrc")


def check_shell_integration():
    path = zshrc_path()

    if not os.path.exists(path):
        return "todo", f"add {SHELL_INTEGRATION} to {path}", "zsh integration"

    with open(path, "r", encoding="utf-8") as file:
        content = file.read()

    for line in content.splitlines():
        stripped = line.strip()

        if SHELL_INTEGRATION in line and not stripped.startswith("#"):
            return "ok", f"{path} contains {SHELL_INTEGRATION}", "zsh integration"

    if SHELL_INTEGRATION in content:
        return (
            "todo",
            f"{path} contains {SHELL_INTEGRATION} only in a commented line",
            "zsh integration",
        )

    return "todo", f"add {SHELL_INTEGRATION} to {path}", "zsh integration"


def expanded_config_path():
    return os.path.expanduser(CONFIG_PATH)


def expanded_tools_config_path():
    return os.path.expanduser(TOOLS_CONFIG_PATH)


def read_text(path):
    path = os.path.expanduser(path)

    if not os.path.exists(path):
        return ""

    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def write_text(path, content):
    path = os.path.expanduser(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        file.write(content)

    return path


def read_config_text():
    return read_text(CONFIG_PATH)


def read_tools_config_text():
    return read_text(TOOLS_CONFIG_PATH)


def write_config_text(content):
    return write_text(CONFIG_PATH, content)


def write_tools_config_text(content):
    return write_text(TOOLS_CONFIG_PATH, content)


def builtin_tools():
    from chiyo_cli.tool_loader import discover_builtin_tools

    return discover_builtin_tools().tools


def builtin_tools_by_cmd():
    return {tool.cmd: tool for tool in builtin_tools()}


def builtin_tools_by_key():
    return {tool.key: tool for tool in builtin_tools()}


def builtin_config_targets():
    by_cmd = builtin_tools_by_cmd()
    by_key = builtin_tools_by_key()
    return set(by_cmd) | set(by_key)


def config_tool_metadata(tool):
    by_cmd = builtin_tools_by_cmd()

    if tool in by_cmd:
        return by_cmd[tool]

    return builtin_tools_by_key().get(tool)


def format_tool_config(tool):
    from chiyo_cli.config import format_module_config
    from chiyo_cli.tool_loader import load_tool_class
    from chiyo_cli.tool_config import tool_config_defaults

    metadata = config_tool_metadata(tool)
    tool_class = load_tool_class(metadata.path)
    return format_module_config(
        metadata.key,
        tool_config_defaults(metadata, tool_class.default_config),
    ).strip()


def format_config_section(target):
    if target == CHIYO_CONFIG_TARGET:
        from chiyo_cli.tool_config import format_chiyo_config

        return format_chiyo_config().strip()

    return format_tool_config(target)


def is_configured(content, tool):
    from chiyo_cli.config import is_module_header

    return any(is_module_header(line, tool) for line in content.splitlines())


def is_exact_header(line, tool):
    from chiyo_cli.config import parse_table_name

    stripped = line.strip()

    if not stripped.startswith("[") or not stripped.endswith("]"):
        return False

    return parse_table_name(stripped.strip("[]").strip()) == tool


def is_nested_header(line, tool):
    from chiyo_cli.config import parse_table_name

    stripped = line.strip()

    if not stripped.startswith("[") or not stripped.endswith("]"):
        return False

    table_name = parse_table_name(stripped.strip("[]").strip())
    return table_name.startswith(f"{tool}.")


def config_key(line):
    stripped = line.strip()

    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None

    return stripped.split("=", 1)[0].strip()


def main_table_lines(tool):
    lines = []

    for line in format_config_section(tool).splitlines():
        stripped = line.strip()

        if not stripped:
            continue

        if stripped.startswith("[") and stripped.endswith("]"):
            if lines:
                break

            lines.append(line)
            continue

        if lines:
            lines.append(line)

    return lines


def append_missing_main_table_defaults(content, tool):
    default_lines = main_table_lines(tool)

    if not default_lines:
        return content, False

    default_key_lines = [
        line
        for line in default_lines[1:]
        if config_key(line) is not None
    ]

    lines = content.splitlines()
    table_start = None
    first_nested = None
    present_keys = set()
    in_exact_table = False

    for index, line in enumerate(lines):
        stripped = line.strip()
        is_header = stripped.startswith("[") and stripped.endswith("]")

        if is_exact_header(line, tool):
            table_start = index
            in_exact_table = True
            continue

        if is_nested_header(line, tool) and first_nested is None:
            first_nested = index

        if is_header:
            in_exact_table = False
            continue

        if in_exact_table:
            key = config_key(line)

            if key is not None:
                present_keys.add(key)

    missing_lines = [
        line
        for line in default_key_lines
        if config_key(line) not in present_keys
    ]

    if not missing_lines:
        return content, False

    if table_start is None:
        insert_index = first_nested if first_nested is not None else len(lines)
        insertion = default_lines

        if insert_index > 0 and lines[insert_index - 1].strip():
            insertion = [""] + insertion

        if insert_index < len(lines) and lines[insert_index].strip():
            insertion = insertion + [""]

        new_lines = lines[:insert_index] + insertion + lines[insert_index:]
        return "\n".join(new_lines).strip() + "\n", True

    insert_index = table_start + 1
    new_lines = lines[:insert_index] + missing_lines + lines[insert_index:]
    return "\n".join(new_lines).strip() + "\n", True


def append_config_sections(content, tools):
    sections = [format_config_section(tool) for tool in tools]
    sections = [section for section in sections if section]

    if not sections:
        return content.strip()

    if content.strip():
        return content.strip() + "\n\n" + "\n\n".join(sections) + "\n"

    return "\n\n".join(sections) + "\n"


def replace_config_sections(content, tools):
    from chiyo_cli.config import remove_module_config

    remaining = content

    for tool in tools:
        remaining = remove_module_config(remaining, tool)

    return append_config_sections(remaining, tools)


def config_init_lines(tools, mode):
    targets = list(dict.fromkeys(config_tool_key(tool) for tool in tools))
    config_targets = [
        target
        for target in targets
        if target == CHIYO_CONFIG_TARGET
    ]
    tool_targets = [
        target
        for target in targets
        if target != CHIYO_CONFIG_TARGET
    ]
    config_content = read_config_text()
    tools_content = read_tools_config_text()
    config_path = expanded_config_path()
    tools_path = expanded_tools_config_path()

    if mode == "write":
        non_empty_paths = []

        if config_targets and config_content.strip():
            non_empty_paths.append(config_path)

        if tool_targets and tools_content.strip():
            non_empty_paths.append(tools_path)

        if non_empty_paths:
            paths = ", ".join(non_empty_paths)
            raise ConfigInitRefused(
                "\n".join(
                    [
                        f"refused config init: {paths} not empty.",
                        "Use --append to add missing sections or --force to replace selected sections.",
                    ]
                )
            )

    def update_content(content, selected_targets, path):
        selected = []
        skipped = []
        defaulted = []

        if mode == "append":
            for target in selected_targets:
                if is_configured(content, target):
                    skipped.append(target)
                else:
                    selected.append(target)
            new_content = append_config_sections(content, selected)

            for target in skipped:
                if not is_configured(new_content, target):
                    continue

                new_content, changed = append_missing_main_table_defaults(
                    new_content,
                    target,
                )

                if changed:
                    defaulted.append(target)
        elif mode == "force":
            selected = list(selected_targets)
            new_content = replace_config_sections(content, selected)
        else:
            selected = list(selected_targets)
            new_content = append_config_sections("", selected)

        lines = []

        for target in selected:
            action = "wrote" if mode == "write" else mode
            lines.append(f"{action} [{target}] config in {path}")

        for target in skipped:
            if mode == "append" and target in defaulted:
                lines.append(f"append [{target}] defaults in {path}")
            else:
                lines.append(f"skip [{target}] config: already exists")

        should_write = bool(selected) or bool(defaulted)
        return new_content, should_write, lines

    lines = []

    if config_targets:
        new_content, should_write, section_lines = update_content(
            config_content,
            config_targets,
            config_path,
        )
        lines.extend(section_lines)

        if should_write:
            write_config_text(new_content)

    if tool_targets:
        new_content, should_write, section_lines = update_content(
            tools_content,
            tool_targets,
            tools_path,
        )
        lines.extend(section_lines)

        if should_write:
            write_tools_config_text(new_content)

    if not lines:
        lines.append("no config changes")

    return lines


def print_config_init(tools, mode):
    for line in config_init_lines(tools, mode):
        print(line)


def validate_config_init_args(args, parser=None):
    if args.all and args.tools:
        raise ValueError("Use either --all or tool names, not both.")

    if not args.all and not args.tools:
        raise ValueError("Specify --all or at least one tool.")

    if args.all:
        from chiyo_cli.tool_config import load_chiyo_config

        config = load_chiyo_config(config_path=CONFIG_PATH)
        builtin_keys = set(builtin_tools_by_key())
        enabled_tools = [
            tool
            for tool in config.get("enabled_tools", [])
            if tool in builtin_keys
        ]
        return [CHIYO_CONFIG_TARGET, *enabled_tools]

    known_targets = builtin_config_targets() | {CHIYO_CONFIG_TARGET}
    unknown_tools = sorted(set(args.tools) - known_targets)

    if unknown_tools:
        raise ValueError(f"Unknown tool config: {', '.join(unknown_tools)}")

    return [config_tool_key(tool) for tool in args.tools]


def config_tool_key(tool):
    metadata = config_tool_metadata(tool)
    return metadata.key if metadata is not None else tool


def config_module_checks():
    content = read_config_text()
    tools_content = read_tools_config_text()

    checks = []

    if is_configured(content, CHIYO_CONFIG_TARGET):
        checks.append(("ok", "[chiyo] exists", "chiyo config"))
    else:
        checks.append(
            (
                "todo",
                "run chiyo config init chiyo --append",
                "chiyo config",
            )
        )

    from chiyo_cli.tool_config import load_chiyo_config

    config = load_chiyo_config(config_path=CONFIG_PATH)

    builtin_keys = set(builtin_tools_by_key())

    for tool in config.get("enabled_tools", []):
        if tool not in builtin_keys:
            continue

        tool_key = tool

        if is_configured(tools_content, tool_key):
            checks.append(("ok", f"[{tool_key}] exists", f"{tool_key} config"))
        else:
            checks.append(
                (
                    "todo",
                    f"run chiyo config init {tool_key} --append",
                    f"{tool_key} config",
                )
            )

    return checks


def command_symlink_checks():
    local_bin_dir = os.path.expanduser(LOCAL_BIN_DIR)

    return [
        check_symlink(
            f"{command} symlink",
            os.path.join(local_bin_dir, command),
            os.path.join(BIN_DIR, command),
        )
        for command in COMMANDS
    ]


def completion_symlink_checks():
    site_functions_dir = os.path.expanduser(ZSH_SITE_FUNCTIONS_DIR)

    return [
        check_symlink(
            f"{completion} completion",
            os.path.join(site_functions_dir, completion),
            os.path.join(COMPLETIONS_DIR, completion),
        )
        for completion in COMPLETIONS
    ]


def user_tool_doctor_checks():
    from chiyo_cli.tool_loader import discover_tools

    config = chiyo_config()
    discovery = discover_tools(config.get("tool_dirs", []), include_builtins=True)
    tools_by_key = {tool.key: tool for tool in discovery.tools}
    cmd_index, duplicate_cmds, cmd_issues = tool_command_index(
        discovery.tools,
        config,
        enabled_only=True,
    )
    checks = []

    for error in discovery.errors:
        checks.append(("warn", error.message, f"user tool {Path(error.path).name}"))

    for tool in discovery.tools:
        checks.append(("ok", tool.path, f"user tool {tool.key} metadata"))

    for enabled in config.get("enabled_tools", []):
        if enabled in tools_by_key:
            checks.append(("ok", "loadable", f"user tool {enabled} enabled"))
        else:
            checks.append(("warn", "enabled but not discoverable", f"user tool {enabled}"))

    for cmd in sorted(duplicate_cmds):
        owners = ", ".join(tool.key for tool in cmd_index[cmd])
        checks.append(("warn", f"duplicate cmd: {owners}", f"user tool {cmd}"))

    for issue in cmd_issues:
        checks.append(("warn", issue.message, f"user tool {issue.tool_key} {issue.cmd}"))

    for tool in discovery.tools:
        wrapper = os.path.expanduser(wrapper_path(tool.cmd, config))
        completion = os.path.expanduser(completion_path(tool.cmd, config))
        wrapper_installed = os.path.exists(wrapper)

        if wrapper_installed and is_generated_wrapper(wrapper, tool.cmd):
            checks.append(("ok", wrapper, f"user tool {tool.key} wrapper"))

            if tool.key not in enabled_tool_keys(config):
                checks.append(
                    (
                        "warn",
                        f"{tool.key} installed but disabled for chiyo run",
                        f"user tool {tool.key}",
                    )
                )
        elif wrapper_installed:
            checks.append(
                (
                    "warn",
                    f"{wrapper} is not a generated chiyo wrapper",
                    f"user tool {tool.key} wrapper",
                )
            )

        if wrapper_installed:
            if os.path.exists(completion) and is_generated_completion(completion, tool.cmd):
                checks.append(("ok", completion, f"user tool {tool.key} zsh"))
            elif os.path.exists(completion):
                checks.append(
                    (
                        "warn",
                        f"{completion} is not a generated chiyo completion",
                        f"user tool {tool.key} zsh",
                    )
                )
            else:
                checks.append(
                    (
                        "warn",
                        f"{completion} not found",
                        f"user tool {tool.key} zsh",
                    )
                )

    return checks


def doctor_lines():
    checks = [
        (*check_command("python3"), "python3"),
        (*check_command("fzf"), "fzf"),
        (*check_command("fd"), "fd"),
        (*check_command("rg"), "rg"),
        (*check_file(CONFIG_PATH), "config"),
        check_path_contains(LOCAL_BIN_DIR),
        check_shell_integration(),
    ]
    checks.extend(command_symlink_checks())
    checks.extend(completion_symlink_checks())
    checks.extend(config_module_checks())
    checks.extend(user_tool_doctor_checks())

    lines = []

    for status, detail, label in checks:
        lines.append(f"{status:7} {label}: {detail}")

    if any(
        status in ("missing", "warn")
        for status, _, label in checks
        if "symlink" in label or "completion" in label
    ):
        lines.append("")
        lines.append("Run: ./install.sh")

    if any(status == "todo" for status, _, _ in checks):
        lines.append("Review todo items above.")

    return lines


def doctor():
    print("\n".join(doctor_lines()))


def enable_tool_lines(tool):
    from chiyo_cli.tool_config import enable_tool

    metadata = tool_metadata_by_command(tool)
    target = metadata.key if metadata is not None else config_tool_key(tool)
    enable_tool(target, config_path=CONFIG_PATH)
    return [f"enabled tool: {target}"]


def disable_tool_lines(tool):
    from chiyo_cli.tool_config import disable_tool

    metadata = tool_metadata_by_command(tool)
    target = metadata.key if metadata is not None else config_tool_key(tool)
    was_enabled = disable_tool(target, config_path=CONFIG_PATH)

    if was_enabled:
        return [f"disabled tool: {target}"]

    return [f"tool already disabled: {target}"]


def print_tool_lines(lines):
    for line in lines:
        print(line)


def tool_list_lines(include_docs=False):
    from chiyo_cli.tool_config import load_chiyo_config
    from chiyo_cli.tool_loader import discover_tools

    config = load_chiyo_config(config_path=CONFIG_PATH)
    enabled_tools = enabled_tool_keys(config)
    discovery = discover_tools(config.get("tool_dirs", []), include_builtins=True)
    cmd_index, duplicate_cmds, _enabled_cmd_issues = tool_command_index(
        discovery.tools,
        config,
        enabled_only=True,
    )
    cmd_issues = configured_cmd_issues(discovery.tools)
    lines = []

    for tool in discovery.tools:
        status = "enabled" if tool.key in enabled_tools else "disabled"
        cmds = ", ".join(configured_cmds(tool))
        lines.append(
            f"{status:8} {tool.name:20} {cmds:16} {tool.author:12} {tool.description}"
        )

        if include_docs:
            docs = tool.docs.strip()

            if docs:
                lines.append("")
                lines.extend(f"  {line}" for line in docs.splitlines())
                lines.append("")

    for error in discovery.errors:
        lines.append(f"warn     {error.path}: {error.message}")

    for cmd in sorted(duplicate_cmds):
        owners = ", ".join(tool.key for tool in cmd_index[cmd])
        lines.append(f"error    duplicate cmd {cmd}: {owners}")

    for issue in cmd_issues:
        lines.append(
            f"error    invalid cmd {issue.cmd}: {issue.tool_key}: {issue.message}"
        )

    if not lines:
        lines.append("no tools found")

    return lines


def tool_metadata_by_command(tool_command):
    from chiyo_cli.tool_resolver import tool_metadata_by_command as resolve_metadata

    return resolve_metadata(
        tool_command,
        config_path=CONFIG_PATH,
        tools_config_path=TOOLS_CONFIG_PATH,
    )


def enabled_tool_keys(config):
    from chiyo_cli.tool_resolver import enabled_tool_keys as resolver_enabled_tool_keys

    return resolver_enabled_tool_keys(config)


def configured_cmds(tool):
    from chiyo_cli.tool_resolver import configured_cmds as resolver_configured_cmds

    return resolver_configured_cmds(tool, config_path=TOOLS_CONFIG_PATH)


def tool_command_index(tools, config, enabled_only=True):
    from chiyo_cli.tool_resolver import tool_command_index as resolver_tool_command_index

    return resolver_tool_command_index(
        tools,
        config,
        enabled_only=enabled_only,
        tools_config_path=TOOLS_CONFIG_PATH,
    )


def configured_cmd_issues(tools):
    from chiyo_cli.tool_resolver import configured_cmd_issues as resolver_configured_cmd_issues

    return resolver_configured_cmd_issues(tools, config_path=TOOLS_CONFIG_PATH)


def duplicate_cmd_message(index, duplicates):
    from chiyo_cli.tool_resolver import duplicate_cmd_message as resolver_duplicate_cmd_message

    return resolver_duplicate_cmd_message(index, duplicates)


def resolve_tool_command(tool_command, enabled_only=True):
    from chiyo_cli.tool_resolver import resolve_tool_command as resolver_resolve_tool_command

    return resolver_resolve_tool_command(
        tool_command,
        enabled_only=enabled_only,
        config_path=CONFIG_PATH,
        tools_config_path=TOOLS_CONFIG_PATH,
    )


def chiyo_config():
    from chiyo_cli.tool_config import load_chiyo_config

    return load_chiyo_config(config_path=CONFIG_PATH)


def wrapper_path(tool_command, config):
    return os.path.join(config["wrapper_dir"], tool_command)


def completion_path(tool_command, config):
    return os.path.join(config["completion_dir"], f"_{tool_command}")


def shell_path(tool_command, config):
    return os.path.join(config["shell_dir"], f"{tool_command}.zsh")


def helper_path(helper_command, config):
    return os.path.join(config["wrapper_dir"], helper_command)


def wrapper_script(tool_command):
    return "\n".join(
        [
            "#!/bin/sh",
            f'exec chiyo run {tool_command} "$@"',
            "",
        ]
    )


def shell_function_script(tool_command):
    return "\n".join(
        [
            f"# Generated by chiyo install {tool_command}",
            f"{tool_command}() {{",
            "  local chiyo_shell_code",
            f'  chiyo_shell_code="$(chiyo shell {tool_command} "$@")" || return',
            '  [ -n "$chiyo_shell_code" ] && eval "$chiyo_shell_code"',
            "}",
            "",
        ]
    )


def completion_script(tool_command):
    return "\n".join(
        [
            "#compdef " + tool_command,
            "",
            "local -a candidates",
            f'candidates=("${{(@f)$(chiyo run {tool_command} --list-completions 2>/dev/null)}}")',
            '_describe "candidates" candidates',
            "",
        ]
    )


def is_generated_wrapper(path, tool_command):
    expanded = os.path.expanduser(path)

    if not os.path.exists(expanded) or os.path.islink(expanded):
        return False

    try:
        content = Path(expanded).read_text(encoding="utf-8")
    except OSError:
        return False

    return content == wrapper_script(tool_command)


def is_generated_completion(path, tool_command):
    expanded = os.path.expanduser(path)

    if not os.path.exists(expanded) or os.path.islink(expanded):
        return False

    try:
        content = Path(expanded).read_text(encoding="utf-8")
    except OSError:
        return False

    return content == completion_script(tool_command)


def is_generated_shell_artifact(path, tool_command):
    expanded = os.path.expanduser(path)

    if not os.path.exists(expanded) or os.path.islink(expanded):
        return False

    try:
        content = Path(expanded).read_text(encoding="utf-8")
    except OSError:
        return False

    return content == shell_function_script(tool_command)


def write_wrapper(path, tool_command):
    expanded = os.path.expanduser(path)
    existing_is_safe = (
        not os.path.exists(expanded)
        or is_generated_wrapper(expanded, tool_command)
    )

    if not existing_is_safe:
        raise ToolCommandError(f"refusing to replace existing file: {expanded}")

    os.makedirs(os.path.dirname(expanded), exist_ok=True)
    temporary = f"{expanded}.tmp"
    Path(temporary).write_text(wrapper_script(tool_command), encoding="utf-8")
    os.chmod(temporary, 0o755)
    os.replace(temporary, expanded)
    return expanded


def write_shell_artifact(path, tool_command):
    expanded = os.path.expanduser(path)
    existing_is_safe = (
        not os.path.exists(expanded)
        or is_generated_shell_artifact(expanded, tool_command)
    )

    if not existing_is_safe:
        raise ToolCommandError(f"refusing to replace existing file: {expanded}")

    os.makedirs(os.path.dirname(expanded), exist_ok=True)
    temporary = f"{expanded}.tmp"
    Path(temporary).write_text(shell_function_script(tool_command), encoding="utf-8")
    os.replace(temporary, expanded)
    return expanded


def write_completion(path, tool_command):
    expanded = os.path.expanduser(path)
    existing_is_safe = (
        not os.path.exists(expanded)
        or is_generated_completion(expanded, tool_command)
    )

    if not existing_is_safe:
        raise ToolCommandError(f"refusing to replace existing file: {expanded}")

    os.makedirs(os.path.dirname(expanded), exist_ok=True)
    temporary = f"{expanded}.tmp"
    Path(temporary).write_text(completion_script(tool_command), encoding="utf-8")
    os.replace(temporary, expanded)
    return expanded


def assert_install_targets_are_safe(tool_command, config, shell_tool=False):
    wrapper = os.path.expanduser(wrapper_path(tool_command, config))
    completion = os.path.expanduser(completion_path(tool_command, config))

    if shell_tool:
        shell = os.path.expanduser(shell_path(tool_command, config))

        if os.path.exists(shell) and not is_generated_shell_artifact(shell, tool_command):
            raise ToolCommandError(f"refusing to replace existing file: {shell}")

        if os.path.exists(completion) and not is_generated_completion(completion, tool_command):
            raise ToolCommandError(f"refusing to replace existing file: {completion}")

        return

    if os.path.exists(wrapper) and not is_generated_wrapper(wrapper, tool_command):
        raise ToolCommandError(f"refusing to replace existing file: {wrapper}")

    if os.path.exists(completion) and not is_generated_completion(completion, tool_command):
        raise ToolCommandError(f"refusing to replace existing file: {completion}")


def resolve_install_target(tool_command):
    resolved = resolve_tool_command(tool_command, enabled_only=False)
    metadata = None if resolved is None else resolved[0]

    if metadata is None:
        raise ToolCommandError(f"unknown tool: {tool_command}")

    install_command = metadata.cmd if "/" in tool_command else tool_command
    return metadata, install_command


def install_resolved_tool_lines(metadata, install_command, config):
    if metadata.shell:
        installed_shell = write_shell_artifact(shell_path(install_command, config), install_command)
        installed_completion = write_completion(completion_path(install_command, config), install_command)
        lines = [
            f"installed {install_command} shell: {installed_shell}",
            f"installed _{install_command}: {installed_completion}",
        ]

        if metadata.key not in enabled_tool_keys(config):
            lines.append(f"warn    {metadata.key} installed but disabled for chiyo run")

        return lines

    installed_path = write_wrapper(wrapper_path(install_command, config), install_command)
    installed_completion = write_completion(completion_path(install_command, config), install_command)
    lines = [
        f"installed {install_command}: {installed_path}",
        f"installed _{install_command}: {installed_completion}",
    ]

    if metadata.key not in enabled_tool_keys(config):
        lines.append(f"warn    {metadata.key} installed but disabled for chiyo run")

    return lines


def install_tool_lines(tool_command):
    config = chiyo_config()
    metadata, install_command = resolve_install_target(tool_command)
    assert_install_targets_are_safe(install_command, config, shell_tool=metadata.shell)
    return install_resolved_tool_lines(metadata, install_command, config)


def install_tools_lines(tool_commands):
    config = chiyo_config()
    targets = [resolve_install_target(tool_command) for tool_command in tool_commands]
    seen = set()

    for metadata, install_command in targets:
        if install_command in seen:
            raise ToolCommandError(f"duplicate install target: {install_command}")

        seen.add(install_command)
        assert_install_targets_are_safe(install_command, config, shell_tool=metadata.shell)

    lines = []

    for metadata, install_command in targets:
        lines.extend(install_resolved_tool_lines(metadata, install_command, config))

    return lines


def uninstall_tool_lines(tool_command):
    config = chiyo_config()
    resolved = resolve_tool_command(tool_command, enabled_only=False)
    metadata = None if resolved is None else resolved[0]
    uninstall_command = metadata.cmd if metadata is not None and "/" in tool_command else tool_command
    path = os.path.expanduser(wrapper_path(uninstall_command, config))
    completion = os.path.expanduser(completion_path(uninstall_command, config))
    lines = []

    if metadata is not None and metadata.shell:
        shell = os.path.expanduser(shell_path(uninstall_command, config))

        if os.path.exists(shell):
            if not is_generated_shell_artifact(shell, uninstall_command):
                raise ToolCommandError(f"refusing to remove non-chiyo shell file: {shell}")

            os.unlink(shell)
            lines.append(f"uninstalled {uninstall_command} shell: {shell}")
        else:
            lines.append(f"not installed: {uninstall_command}")

        if os.path.exists(completion):
            if not is_generated_completion(completion, uninstall_command):
                raise ToolCommandError(
                    f"refusing to remove non-chiyo completion: {completion}"
                )

            os.unlink(completion)
            lines.append(f"uninstalled _{uninstall_command}: {completion}")

        for helper in LEGACY_SHELL_HELPERS.get(uninstall_command, []):
            helper_file = os.path.expanduser(helper_path(helper, config))
            source = os.path.join(BIN_DIR, helper)

            if os.path.islink(helper_file) and os.readlink(helper_file) == source:
                os.unlink(helper_file)
                lines.append(f"uninstalled {helper}: {helper_file}")

        return lines

    if os.path.exists(path):
        if not is_generated_wrapper(path, uninstall_command):
            raise ToolCommandError(f"refusing to remove non-chiyo wrapper: {path}")

        os.unlink(path)
        lines.append(f"uninstalled {uninstall_command}: {path}")
    else:
        lines.append(f"not installed: {uninstall_command}")

    if os.path.exists(completion):
        if not is_generated_completion(completion, uninstall_command):
            raise ToolCommandError(
                f"refusing to remove non-chiyo completion: {completion}"
            )

        os.unlink(completion)
        lines.append(f"uninstalled _{uninstall_command}: {completion}")

    return lines


def uninstall_tools_lines(tool_commands):
    targets = []
    seen = set()

    for tool_command in tool_commands:
        resolved = resolve_tool_command(tool_command, enabled_only=False)
        metadata = None if resolved is None else resolved[0]
        uninstall_command = metadata.cmd if metadata is not None and "/" in tool_command else tool_command

        if uninstall_command in seen:
            raise ToolCommandError(f"duplicate uninstall target: {uninstall_command}")

        seen.add(uninstall_command)
        targets.append(tool_command)

    lines = []

    for tool_command in targets:
        lines.extend(uninstall_tool_lines(tool_command))

    return lines


def run_tool(tool_command, tool_args, execute_shell_actions=True):
    from chiyo_cli.tool_config import load_tool_config, tool_config_defaults
    from chiyo_cli.tool_loader import load_tool_class

    resolved = resolve_tool_command(tool_command, enabled_only=True)

    if resolved is None:
        raise ToolCommandError(f"unknown tool: {tool_command}")

    metadata, _config = resolved
    tool_class = load_tool_class(metadata.path)
    tool = tool_class()
    tool_config = load_tool_config(
        metadata.key,
        tool_config_defaults(metadata, tool.default_config),
        config_path=TOOLS_CONFIG_PATH,
    )
    if execute_shell_actions:
        return tool.run(tool_args, config=tool_config)

    return tool.run(
        tool_args,
        config=tool_config,
        execute_shell_actions=False,
    )


def shell_tool_lines(tool_command, tool_args):
    from chiyo_cli.toolkit import ShellAction

    result = run_tool(
        tool_command,
        tool_args,
        execute_shell_actions=False,
    )

    if result is None:
        return []

    if not isinstance(result, ShellAction):
        result = ShellAction.print(result)

    rendered = result.render_shell()

    if not rendered:
        return []

    return [rendered]


def tool_doc_lines(tool_command):
    try:
        resolved = resolve_tool_command(tool_command, enabled_only=False)
    except ToolCommandError as error:
        return [str(error)]

    tool = None if resolved is None else resolved[0]

    if tool is None:
        return None

    docs = tool.docs.strip()

    if not docs:
        return [f"{tool.command}: no docs available."]

    return docs.splitlines()


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if args.command == "init":
        print_init(args.shell)
        return

    if args.command == "doctor":
        doctor()
        return

    if args.command == "doc":
        lines = tool_doc_lines(args.tool)

        if lines is None:
            print(f"chiyo doc: unknown tool: {args.tool}", file=sys.stderr)
            sys.exit(1)

        print_tool_lines(lines)
        return

    if args.command == "run":
        try:
            run_tool(args.tool, args.tool_args)
        except ToolCommandError as error:
            print(f"chiyo run: {error}", file=sys.stderr)
            sys.exit(1)
        return

    if args.command == "shell":
        try:
            print_tool_lines(shell_tool_lines(args.tool, args.tool_args))
        except ToolCommandError as error:
            print(f"chiyo shell: {error}", file=sys.stderr)
            sys.exit(1)
        return

    if args.command == "install":
        try:
            print_tool_lines(install_tools_lines(args.tools))
        except ToolCommandError as error:
            print(f"chiyo install: {error}", file=sys.stderr)
            sys.exit(1)
        return

    if args.command == "uninstall":
        try:
            print_tool_lines(uninstall_tools_lines(args.tools))
        except ToolCommandError as error:
            print(f"chiyo uninstall: {error}", file=sys.stderr)
            sys.exit(1)
        return

    if args.command == "config":
        if args.config_command == "init":
            try:
                tools = validate_config_init_args(args)
            except ValueError as error:
                print(f"chiyo config init: {error}", file=sys.stderr)
                sys.exit(2)

            try:
                print_config_init(tools, args.config_mode)
            except ConfigInitRefused as error:
                print(error, file=sys.stderr)
                sys.exit(1)
            return

    if args.command == "tool":
        if args.tool_command == "list":
            print_tool_lines(tool_list_lines(include_docs=args.docs))
            return

        if args.tool_command == "enable":
            print_tool_lines(enable_tool_lines(args.tool))
            return

        if args.tool_command == "disable":
            print_tool_lines(disable_tool_lines(args.tool))
            return


if __name__ == "__main__":
    main()
