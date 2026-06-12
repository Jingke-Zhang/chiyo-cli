"""Framework-backed app built-in."""

import os
import shutil
import subprocess
import sys

from chiyo_cli.fzf import STYLE_PRIMARY, STYLE_SECONDARY
from chiyo_cli.toolkit import Field, PickOpenTool


DEFAULT_CONFIG = {
    "fzf_prompt": "app> ",
    "alias": {},
}


def app_name_from_path(path):
    name = os.path.basename(path)

    if name.endswith(".app"):
        name = name[:-4]

    return name


def discover_apps(fail):
    if shutil.which("mdfind") is None:
        fail("macOS 'mdfind' command is not available.")

    result = subprocess.run(
        ["mdfind", 'kMDItemContentType == "com.apple.application-bundle"'],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        detail = result.stderr.strip() or "unknown error"
        fail(f"could not discover applications: {detail}")

    apps = []
    seen_paths = set()

    for path in result.stdout.splitlines():
        if path in seen_paths:
            continue

        name = app_name_from_path(path)

        if not name:
            continue

        seen_paths.add(path)
        apps.append({"name": name, "path": path})

    return sorted(apps, key=lambda app: (app["name"].lower(), app["path"].lower()))


def resolve_alias(query, aliases):
    if not query:
        return None

    return aliases.get(query)


def alias_for_app(name, aliases):
    matching_aliases = [
        alias
        for alias, app_name in aliases.items()
        if app_name == name
    ]

    if not matching_aliases:
        return ""

    return sorted(matching_aliases, key=str.lower)[0]


def open_app(app, fail):
    if shutil.which("open") is None:
        fail("macOS 'open' command is not available.")

    if app.get("path"):
        command = ["open", app["path"]]
    else:
        command = ["open", "-a", app["name"]]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        detail = result.stderr.strip() or "unknown error"
        fail(f"could not open application '{app['name']}': {detail}")


class Tool(PickOpenTool):
    name = "Application Launcher"
    command = "app"
    author = "Chiyo CLI"
    description = "Search installed macOS applications."
    docs = """
    # app

    Search installed macOS applications, resolve configured aliases, and launch
    the selected application.
    """
    prompt = "app> "
    default_config = DEFAULT_CONFIG
    search_display_fields = [1, 2]

    def add_arguments(self, parser):
        parser.add_argument(
            "--print-name",
            action="store_true",
            help="Print the selected application name instead of opening it.",
        )

    def items(self, config):
        return discover_apps(self.fail)

    def match(self, item, query, config):
        if not query:
            return True

        aliases = config.get("alias", {})
        query = query.lower()
        return (
            query in item["name"].lower()
            or query in alias_for_app(item["name"], aliases).lower()
        )

    def display_fields(self, item, config):
        alias = alias_for_app(item["name"], config.get("alias", {}))

        if alias:
            name_style = ""
            alias_style = STYLE_PRIMARY
        else:
            name_style = STYLE_PRIMARY
            alias_style = ""

        return [
            Field(item["name"], name_style),
            Field(alias, alias_style),
            Field(item["path"], STYLE_SECONDARY),
        ]

    def completion_items(self, config):
        return self.items(config)

    def completion_label(self, item, config):
        return item["name"]

    def run(self, argv=None, config=None):
        config = dict(self.default_config if config is None else config)
        args = self.parser().parse_args(argv if argv is not None else sys.argv[1:])

        if args.list_completions:
            self.print_completions(config)
            return None

        query = self.query_from_args(args)
        alias_target = resolve_alias(query, config.get("alias", {}))

        if alias_target and not args.confirm:
            selected = {"name": alias_target, "path": None}
            return self.open_item(selected, args, config)

        return super().run(argv=argv, config=config)

    def open_item(self, item, args, config):
        if args.print_name:
            print(item["name"])
            return item["name"]

        open_app(item, self.fail)
        return item
