from chiyo_cli.api import ChiyoTool


class Tool(ChiyoTool):
    name = "Paper Search"
    command = "paper"
    author = "Fixture Author"
    description = "Search fixture papers and open PDFs."
    docs = """
    # Paper Search

    Search fixture papers and open PDFs.
    """
    default_config = {
        "root": ".",
    }

    def items(self, config):
        return [
            {
                "title": path.stem,
                "path": str(path),
            }
            for path in self.glob_paths(config["root"], "*.pdf")
        ]

    def match(self, item, query, config):
        if not query:
            return True

        return all(term in item["title"].lower() for term in query.lower().split())

    def sort_key(self, item, config):
        return item["title"].lower()

    def display_fields(self, item, config):
        return [
            self.primary(item["title"]),
            self.secondary(item["path"]),
        ]

    def completion_label(self, item, config):
        return item["title"]

    def open_item(self, item, args, config):
        return item["path"]
