from chiyo_cli.api import ChiyoTool


class Tool(ChiyoTool):
    name = "Disabled Notes"
    cmd = "disabled-notes"
    author = "Fixture Author"
    author_id = "fixture"
    description = "Fixture tool used for disabled-tool tests."
    docs = "Fixture tool used for disabled-tool tests."

    def items(self, config):
        return [{"title": "Note"}]

    def display_fields(self, item, config):
        return [self.primary(item["title"])]

    def open_item(self, item, args, config):
        return item
