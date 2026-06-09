from pathlib import Path

from chiyo_cli.toolkit import Field, PickOpenTool, STYLE_PRIMARY, STYLE_SECONDARY


class Tool(PickOpenTool):
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
        root = Path(config["root"])
        return [
            {
                "title": path.stem,
                "path": str(path),
            }
            for path in sorted(root.glob("*.pdf"))
        ]

    def match(self, item, query, config):
        if not query:
            return True

        return all(term in item["title"].lower() for term in query.lower().split())

    def sort_key(self, item, config):
        return item["title"].lower()

    def display_fields(self, item, config):
        return [
            Field(item["title"], STYLE_PRIMARY),
            Field(item["path"], STYLE_SECONDARY),
        ]

    def completion_label(self, item, config):
        return item["title"]

    def open_item(self, item, args, config):
        return item["path"]
