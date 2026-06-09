from chiyo_cli.toolkit import Field, PickOpenTool, STYLE_PRIMARY


class Tool(PickOpenTool):
    name = "Missing Author"
    command = "missing-author"
    description = "Fixture tool with incomplete metadata."
    docs = "Fixture tool with incomplete metadata."

    def items(self, config):
        return [{"title": "Incomplete"}]

    def display_fields(self, item, config):
        return [Field(item["title"], STYLE_PRIMARY)]

    def open_item(self, item, args, config):
        return item
