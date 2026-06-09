"""Helpers for adapting existing bin scripts into framework-backed tools."""

from importlib.machinery import SourceFileLoader
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_legacy_command(command):
    path = REPO_ROOT / "bin" / command
    module_name = f"chiyo_builtin_legacy_{command.replace('-', '_')}"
    return SourceFileLoader(module_name, str(path)).load_module()
