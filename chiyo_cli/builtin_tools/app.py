"""Framework-backed app built-in."""

from pathlib import Path

from chiyo_cli.toolkit import (
    PickOpenTool,
    ToolError,
    open_location,
    open_with_app,
    run_command,
)


DEFAULT_CONFIG = {
    "fzf_prompt": "app> ",
    "alias": {},
}


def app_name_from_path(path):
    name = Path(path).name

    if name.endswith(".app"):
        name = name[:-4]

    return name


def discover_apps(fail):
    try:
        result = run_command(
            ["mdfind", 'kMDItemContentType == "com.apple.application-bundle"'],
            "could not discover applications",
        )
    except ToolError as error:
        fail(str(error))
        raise

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
    try:
        if app.get("path"):
            open_location(app["path"])
        else:
            open_with_app("", app["name"])
    except ToolError as error:
        fail(f"could not open application '{app['name']}': {error}")


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
        _ = config
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
            name_field = self.plain(item["name"])
            alias_field = self.primary(alias)
        else:
            name_field = self.primary(item["name"])
            alias_field = self.plain(alias)

        return [
            name_field,
            alias_field,
            self.secondary(item["path"]),
        ]

    def completion_items(self, config):
        seen = set()
        items = []

        for item in self.items(config):
            name = item["name"]

            if name in seen:
                continue

            seen.add(name)
            items.append(item)

        return items

    def completion_label(self, item, config):
        _ = config
        return item["name"]

    def run(self, argv=None, config=None, execute_shell_actions=True):
        config = dict(self.default_config if config is None else config)
        args = self.parser().parse_args(argv)

        if args.list_completions:
            self.print_completions(config)
            return None

        query = self.query_from_args(args)
        alias_target = resolve_alias(query, config.get("alias", {}))

        if alias_target and not args.confirm:
            selected = {"name": alias_target, "path": None}
            return self.open_item(selected, args, config)

        return super().run(
            argv=argv,
            config=config,
            execute_shell_actions=execute_shell_actions,
        )

    def open_item(self, item, args, config):
        _ = config

        if args.print_name:
            print(item["name"])
            return item["name"]

        open_app(item, self.fail)
        return item
