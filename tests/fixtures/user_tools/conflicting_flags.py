from chiyo_cli.api import ChiyoTool


class Tool(ChiyoTool):
    name = "Conflicting Flags"
    command = "conflicting-flags"
    author = "Fixture Author"
    description = "Fixture tool with a conflicting framework flag."
    docs = "Fixture tool with a conflicting framework flag."

    def items(self, config):
        return [{"title": "Conflict"}]

    def display_fields(self, item, config):
        return [self.primary(item["title"])]

    def add_arguments(self, parser):
        parser.add_argument("--confirm", action="store_true")

    def open_item(self, item, args, config):
        return item
