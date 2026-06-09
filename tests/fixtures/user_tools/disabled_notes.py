from chiyo_cli.toolkit import Field, PickOpenTool, STYLE_PRIMARY


class Tool(PickOpenTool):
    name = "Disabled Notes"
    command = "disabled-notes"
    author = "Fixture Author"
    description = "Fixture tool used for disabled-tool tests."
    docs = "Fixture tool used for disabled-tool tests."

    def items(self, config):
        return [{"title": "Note"}]

    def display_fields(self, item, config):
        return [Field(item["title"], STYLE_PRIMARY)]

    def open_item(self, item, args, config):
        return item
