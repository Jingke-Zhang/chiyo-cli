"""User-tool loading and metadata validation."""

import importlib.util
import importlib
import re
import sys
import types
from dataclasses import dataclass
from pathlib import Path

from chiyo_cli.paths import expand_path
from chiyo_cli.toolkit import PickOpenTool, ToolFlagError, validate_tool_flags


REQUIRED_METADATA = ["name", "author", "author_id", "description", "docs"]
DESCRIPTION_LIMIT = 80
COMMAND_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")
BUILTIN_TOOL_MODULES = {
    "app": "chiyo_cli.builtin_tools.app",
    "bm": "chiyo_cli.builtin_tools.bm",
    "gop": "chiyo_cli.builtin_tools.gop",
    "proj": "chiyo_cli.builtin_tools.proj",
    "ws": "chiyo_cli.builtin_tools.ws",
    "zo": "chiyo_cli.builtin_tools.zo",
}


class ToolLoadError(Exception):
    """Raised when a tool file cannot be loaded or validated."""


@dataclass(frozen=True)
class ToolMetadata:
    name: str
    author: str
    author_id: str
    key: str
    cmd: str
    command: str
    description: str
    docs: str
    path: str


@dataclass(frozen=True)
class ToolDiscoveryError:
    path: str
    message: str


@dataclass(frozen=True)
class ToolDiscovery:
    tools: list
    errors: list


def load_module_from_path(path):
    if str(path).startswith("builtin:"):
        command = str(path).split(":", 1)[1]
        module_name = BUILTIN_TOOL_MODULES.get(command)

        if module_name is None:
            raise ToolLoadError(f"unknown built-in tool: {command}")

        return importlib.import_module(module_name)

    path = Path(path)

    if path.name == "tool.py":
        return load_directory_tool_module(path)

    module_name = f"chiyo_user_tool_{path.stem}_{abs(hash(str(path)))}"
    spec = importlib.util.spec_from_file_location(module_name, path)

    if spec is None or spec.loader is None:
        raise ToolLoadError(f"could not load tool module: {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_directory_tool_module(path):
    path = Path(path)
    package_dir = path.parent
    package_name = f"chiyo_user_tool_{package_dir.name}_{abs(hash(str(package_dir)))}"
    module_name = f"{package_name}.tool"
    package = types.ModuleType(package_name)
    package.__path__ = [str(package_dir)]
    package.__package__ = package_name
    sys.modules[package_name] = package

    spec = importlib.util.spec_from_file_location(module_name, path)

    if spec is None or spec.loader is None:
        raise ToolLoadError(f"could not load tool module: {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_tool_class(path):
    module = load_module_from_path(path)
    tool_class = getattr(module, "Tool", None)

    if tool_class is None:
        raise ToolLoadError(f"tool file has no Tool class: {path}")

    validate_tool_class(tool_class, path)
    return tool_class


def validate_tool_class(tool_class, path=None):
    if not isinstance(tool_class, type) or not issubclass(tool_class, PickOpenTool):
        location = f": {path}" if path is not None else ""
        raise ToolLoadError(f"Tool must subclass PickOpenTool{location}")

    missing = [
        field
        for field in REQUIRED_METADATA
        if not getattr(tool_class, field, None)
    ]

    if missing:
        fields = ", ".join(missing)
        location = f": {path}" if path is not None else ""
        raise ToolLoadError(f"tool metadata missing {fields}{location}")

    description = getattr(tool_class, "description")

    if len(description) > DESCRIPTION_LIMIT:
        location = f": {path}" if path is not None else ""
        raise ToolLoadError(
            f"tool description must be {DESCRIPTION_LIMIT} characters or fewer{location}"
        )

    command = default_tool_cmd(tool_class)

    if not isinstance(command, str) or not COMMAND_PATTERN.fullmatch(command):
        location = f": {path}" if path is not None else ""
        raise ToolLoadError(
            "tool cmd must match ^[a-z][a-z0-9-]*$"
            f"{location}"
        )

    try:
        validate_tool_flags(tool_class())
    except ToolFlagError as error:
        location = f": {path}" if path is not None else ""
        raise ToolLoadError(f"{error}{location}") from error


def metadata_from_tool_class(tool_class, path):
    validate_tool_class(tool_class, path)
    cmd = default_tool_cmd(tool_class)
    author_id = tool_class.author_id
    return ToolMetadata(
        name=tool_class.name,
        author=tool_class.author,
        author_id=author_id,
        key=f"{author_id}/{cmd}",
        cmd=cmd,
        command=cmd,
        description=tool_class.description,
        docs=tool_class.docs,
        path=str(Path(path)),
    )


def default_tool_cmd(tool_class):
    return getattr(tool_class, "cmd", None) or getattr(tool_class, "command", None)


def load_tool_metadata(path):
    tool_class = load_tool_class(path)
    return metadata_from_tool_class(tool_class, path)


def discover_tool_paths(tool_dirs):
    paths = []

    for tool_dir in tool_dirs:
        directory = Path(expand_path(tool_dir))

        if not directory.is_dir():
            continue

        paths.extend(
            path
            for path in directory.glob("*.py")
            if not path.name.startswith("_")
        )
        paths.extend(
            path
            for path in directory.glob("*/tool.py")
            if not path.parent.name.startswith("_")
        )

    return sorted(paths, key=tool_path_sort_key)


def tool_path_sort_key(path):
    if path.name == "tool.py":
        name = path.parent.name
    else:
        name = path.stem

    return name.lower(), str(path)


def discover_user_tools(tool_dirs):
    tools = []
    errors = []

    for path in discover_tool_paths(tool_dirs):
        try:
            tools.append(load_tool_metadata(path))
        except ToolLoadError as error:
            errors.append(ToolDiscoveryError(str(path), str(error)))

    return ToolDiscovery(
        sorted(tools, key=lambda tool: tool.key.lower()),
        errors,
    )


def discover_builtin_tools():
    tools = []
    errors = []

    for command in sorted(BUILTIN_TOOL_MODULES):
        path = f"builtin:{command}"

        try:
            tools.append(load_tool_metadata(path))
        except ToolLoadError as error:
            errors.append(ToolDiscoveryError(path, str(error)))

    return ToolDiscovery(tools, errors)


def discover_tools(tool_dirs, include_builtins=False):
    discovery = discover_user_tools(tool_dirs)

    if not include_builtins:
        return discovery

    builtins = discover_builtin_tools()

    return ToolDiscovery(
        sorted([*builtins.tools, *discovery.tools], key=lambda tool: tool.key.lower()),
        [*builtins.errors, *discovery.errors],
    )
