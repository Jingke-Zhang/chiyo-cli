"""Framework-backed tmux workspace built-in."""

import os
import re
import subprocess
from pathlib import Path

from chiyo_cli.builtin_tools import project
from chiyo_cli.paths import compact_path, expand_path
from chiyo_cli.toolkit import Field, PickOpenTool, STYLE_PRIMARY, STYLE_SECONDARY, ToolError, require_command


SESSION_PATTERN = re.compile(r"[^A-Za-z0-9_.-]+")
DEFAULT_CONFIG = {
    "roots": ["~/Documents", "~/Projects", "~/Developer"],
    "markers": [".project", ".git"],
    "exclude": ["node_modules", "Library", ".cache"],
    "session_prefix": "",
    "fzf_prompt": "ws> ",
    "alias": {},
}


def session_name(value, prefix=""):
    name = Path(str(value).rstrip("/")).name or str(value)
    normalized = SESSION_PATTERN.sub("-", name.strip()).strip("-_.")

    if not normalized:
        normalized = "workspace"

    return f"{prefix}{normalized}"


def run_tmux(args, fail, allow_failure=False):
    try:
        require_command("tmux")
    except ToolError as error:
        fail(str(error))

    result = subprocess.run(
        ["tmux", *args],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0 and not allow_failure:
        detail = result.stderr.strip() or "unknown error"
        fail(f"tmux {' '.join(args)} failed: {detail}")

    return result


def tmux_sessions(fail):
    result = run_tmux(
        ["list-sessions", "-F", "#{session_name}\t#{session_path}"],
        fail,
        allow_failure=True,
    )

    if result.returncode != 0:
        return []

    sessions = []

    for line in result.stdout.splitlines():
        name, _, path = line.partition("\t")

        if not name:
            continue

        sessions.append(
            {
                "kind": "session",
                "name": name,
                "session": name,
                "path": path,
                "exists": True,
            }
        )

    return sessions


def alias_workspaces(alias_config, prefix=""):
    items = []

    for name, path in sorted(alias_config.items()):
        expanded = expand_path(path)
        items.append(
            {
                "kind": "alias",
                "name": name,
                "session": session_name(name, prefix),
                "path": expanded,
                "exists": False,
            }
        )

    return items


def project_workspaces(config, fail):
    roots = project.normalize_roots(config["roots"], fail)
    paths = project.all_projects(
        roots,
        config["markers"],
        config["exclude"],
        fail,
    )
    return [
        {
            "kind": "project",
            "name": project.project_name(path),
            "session": session_name(path, config["session_prefix"]),
            "path": path,
            "exists": False,
        }
        for path in paths
    ]


def merge_workspaces(items):
    seen = set()
    merged = []

    for item in items:
        key = item["session"]

        if key in seen:
            continue

        seen.add(key)
        merged.append(item)

    return merged


def session_exists(name, sessions):
    return any(session["session"] == name for session in sessions)


def create_session(name, path, fail):
    run_tmux(["new-session", "-d", "-s", name, "-c", path], fail)


def attach_or_switch(name, fail):
    if os.environ.get("TMUX"):
        run_tmux(["switch-client", "-t", name], fail)
    else:
        run_tmux(["attach-session", "-t", name], fail)

    return name


def kill_session(name, fail):
    run_tmux(["kill-session", "-t", name], fail)
    return name


def rename_session(old_name, new_name, fail):
    run_tmux(["rename-session", "-t", old_name, new_name], fail)
    return new_name


class Tool(PickOpenTool):
    name = "Workspace"
    cmd = "ws"
    author = "Chiyo CLI"
    author_id = "Jingke-Zhang"
    description = "Manage tmux workspaces."
    docs = """
    # ws

    Manage tmux workspaces backed by sessions, aliases, and project roots.
    """
    prompt = "ws> "
    default_config = DEFAULT_CONFIG
    search_display_fields = [1, 2, 3]

    def add_arguments(self, parser):
        parser.add_argument(
            "-r",
            "--root",
            action="append",
            help="Search this directory instead of configured roots. Can be used more than once.",
        )
        parser.add_argument(
            "-E",
            "--exclude",
            action="append",
            help="Exclude a glob pattern from project search. Can be used more than once.",
        )
        parser.add_argument(
            "--new",
            nargs=2,
            metavar=("NAME", "PATH"),
            help="Create a workspace session for PATH and enter it.",
        )
        parser.add_argument(
            "--kill",
            action="store_true",
            help="Kill the selected tmux session.",
        )
        parser.add_argument(
            "--rename",
            nargs=2,
            metavar=("OLD", "NEW"),
            help="Rename an existing tmux session.",
        )

    def query_from_args(self, args):
        self._root_args = args.root
        self._exclude_args = args.exclude or []
        return super().query_from_args(args)

    def normalize_config(self, config):
        normalized = dict(config)

        root_args = getattr(self, "_root_args", None)
        exclude_args = getattr(self, "_exclude_args", [])

        if root_args:
            normalized["roots"] = root_args

        normalized["exclude"] = list(config["exclude"]) + exclude_args
        return normalized

    def sessions(self):
        return tmux_sessions(self.fail)

    def items(self, config):
        config = self.normalize_config(config)
        sessions = self.sessions()
        session_names = {item["session"] for item in sessions}
        aliases = alias_workspaces(config.get("alias", {}), config["session_prefix"])
        projects = project_workspaces(config, self.fail)

        for item in [*aliases, *projects]:
            item["exists"] = item["session"] in session_names

        return merge_workspaces([*sessions, *aliases, *projects])

    def match(self, item, query, config):
        if not query:
            return True

        haystack = " ".join(
            str(item.get(key, ""))
            for key in ("name", "session", "path", "kind")
        ).lower()
        return query.lower() in haystack

    def sort_key(self, item, config):
        order = {"session": 0, "alias": 1, "project": 2}
        return order.get(item["kind"], 9), item["name"].lower()

    def display_fields(self, item, config):
        status = "attached" if item.get("exists") else "new"
        path = compact_path(item["path"]) if item.get("path") else ""
        return [
            Field(item["name"], STYLE_PRIMARY),
            Field(item["kind"], STYLE_SECONDARY),
            Field(status),
            Field(path, STYLE_SECONDARY),
        ]

    def completion_items(self, config):
        return self.items(config)

    def completion_label(self, item, config):
        return item["name"]

    def select_item(self, items, query, args, config):
        if query and not args.confirm and len(items) == 1:
            return items[0]

        return super().select_item(items, query, args, config)

    def open_item(self, item, args, config):
        sessions = self.sessions()

        if item["kind"] != "session" and not session_exists(item["session"], sessions):
            create_session(item["session"], item["path"], self.fail)

        return attach_or_switch(item["session"], self.fail)

    def run(self, argv=None, config=None, execute_shell_actions=True):
        config = dict(self.default_config if config is None else config)
        args = self.parser().parse_args(argv)
        self.query_from_args(args)
        config = self.normalize_config(config)

        if args.new:
            name, path = args.new
            session = session_name(name, config["session_prefix"])
            create_session(session, expand_path(path), self.fail)
            return attach_or_switch(session, self.fail)

        if args.rename:
            old_name, new_name = args.rename
            return rename_session(
                old_name,
                session_name(new_name, config["session_prefix"]),
                self.fail,
            )

        if args.kill:
            query = " ".join(args.query)
            sessions = self.filtered_items(self.sessions(), query, config)

            if not sessions:
                self.fail("no sessions found.")

            selected = self.select_item(sessions, query, args, config)

            if selected is None:
                return None

            return kill_session(selected["session"], self.fail)

        return super().run(
            argv,
            config=config,
            execute_shell_actions=execute_shell_actions,
        )
