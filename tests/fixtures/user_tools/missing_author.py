from chiyo_cli.api import ChiyoTool


class Tool(ChiyoTool):
    name = "Missing Author"
    cmd = "missing-author"
    author_id = "fixture"
    description = "Fixture tool with incomplete metadata."
    docs = "Fixture tool with incomplete metadata."

    def items(self, config):
        return [{"title": "Incomplete"}]

    def display_fields(self, item, config):
        return [self.primary(item["title"])]

    def open_item(self, item, args, config):
        return item
