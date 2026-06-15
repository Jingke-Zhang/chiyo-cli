"""Setup diagnostics and shell initialization for Chiyo CLI."""

import os
from pathlib import Path
import shutil

from chiyo_cli.commands.install import (
    BIN_DIR,
    completion_path,
    is_generated_completion,
    is_generated_shell_artifact,
    is_generated_wrapper,
    shell_path,
    wrapper_path,
)


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
COMPLETIONS_DIR = os.path.join(REPO_ROOT, "completions")
CONFIG_PATH = "~/.config/chiyo-cli/config.toml"
TOOLS_CONFIG_PATH = "~/.config/chiyo-cli/tools.toml"
LOCAL_BIN_DIR = "~/.local/bin"
ZSH_SITE_FUNCTIONS_DIR = "~/.local/share/zsh/site-functions"
COMMANDS = ["chiyo"]
COMPLETIONS = []
SHELL_INTEGRATION = 'eval "$(chiyo init zsh)"'
CHIYO_CONFIG_TARGET = "chiyo"


def chiyo_config():
    from chiyo_cli.tool_config import load_chiyo_config

    return load_chiyo_config(config_path=CONFIG_PATH)


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


def is_configured(content, tool):
    from chiyo_cli.config import is_module_header

    return any(is_module_header(line, tool) for line in content.splitlines())


def read_text(path):
    path = os.path.expanduser(path)

    if not os.path.exists(path):
        return ""

    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def read_config_text():
    return read_text(CONFIG_PATH)


def read_tools_config_text():
    return read_text(TOOLS_CONFIG_PATH)


def builtin_tools_by_key():
    from chiyo_cli.tool_loader import discover_builtin_tools

    return {tool.key: tool for tool in discover_builtin_tools().tools}


def enabled_tool_keys(config):
    from chiyo_cli.tool_resolver import enabled_tool_keys as resolver_enabled_tool_keys

    return resolver_enabled_tool_keys(config)


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

        if is_configured(tools_content, tool):
            checks.append(("ok", f"[{tool}] exists", f"{tool} config"))
        else:
            checks.append(
                (
                    "todo",
                    f"run chiyo config init {tool} --append",
                    f"{tool} config",
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
        shell = os.path.expanduser(shell_path(tool.cmd, config))
        wrapper_installed = os.path.exists(wrapper)
        shell_installed = os.path.exists(shell)

        if tool.shell:
            if shell_installed and is_generated_shell_artifact(shell, tool.cmd):
                checks.append(("ok", shell, f"user tool {tool.key} shell"))

                if tool.key not in enabled_tool_keys(config):
                    checks.append(
                        (
                            "warn",
                            f"{tool.key} installed but disabled for chiyo run",
                            f"user tool {tool.key}",
                        )
                    )
            elif shell_installed:
                checks.append(
                    (
                        "warn",
                        f"{shell} is not a generated chiyo shell artifact",
                        f"user tool {tool.key} shell",
                    )
                )

            if wrapper_installed and is_generated_wrapper(wrapper, tool.cmd):
                checks.append(
                    (
                        "warn",
                        f"{wrapper} is an old generated wrapper; run chiyo install {tool.cmd}",
                        f"user tool {tool.key} wrapper",
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

            if shell_installed:
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

            continue

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
