"""Framework-backed web search built-in."""

from urllib.parse import quote

from chiyo_cli.toolkit import PickOpenTool


DEFAULT_ENGINES = {
    "g": {
        "name": "Google",
        "url": "https://www.google.com/search?q={query}",
    },
    "gh": {
        "name": "GitHub",
        "url": "https://github.com/search?q={query}",
    },
    "ytb": {
        "name": "YouTube",
        "url": "https://www.youtube.com/results?search_query={query}",
    },
    "scholar": {
        "name": "Google Scholar",
        "url": "https://scholar.google.com/scholar?q={query}",
    },
}


def build_search_url(engine, query):
    return engine["url"].replace("{query}", quote(query))


class Tool(PickOpenTool):
    name = "Web Search"
    cmd = "s"
    author = "Chiyo CLI"
    author_id = "shiori-route"
    description = "Open a configured web search engine."
    docs = """
    # s

    Open a configured web search URL. The first query term selects an engine
    when it matches a configured engine key.
    """
    prompt = "s> "
    default_config = {
        "fzf_prompt": "s> ",
        "engines": DEFAULT_ENGINES,
    }
    search_display_fields = [1, 2]

    def parser(self):
        parser = super().parser()
        parser.set_defaults(selected_engine=None)
        return parser

    def items(self, config):
        return [
            {
                "key": key,
                "name": engine["name"],
                "url": engine["url"],
            }
            for key, engine in config["engines"].items()
        ]

    def query_from_args(self, args):
        terms = list(args.query)

        if terms and terms[0] in self._engine_keys:
            args.selected_engine = terms[0]
            self._selected_engine = terms[0]
            return " ".join(terms[1:])

        args.selected_engine = None
        self._selected_engine = None
        return " ".join(terms)

    def filtered_items(self, items, query, config):
        if self._selected_engine is None:
            return super().filtered_items(items, query, config)

        return [
            item
            for item in items
            if item["key"] == self._selected_engine
        ]

    def match(self, item, query, config):
        if not query:
            return True

        haystack = f'{item["key"]} {item["name"]}'.lower()
        return all(term in haystack for term in query.lower().split())

    def sort_key(self, item, config):
        return item["key"]

    def display_fields(self, item, config):
        return [
            self.primary(item["key"]),
            self.plain(item["name"]),
        ]

    def completion_items(self, config):
        return self.items(config)

    def completion_label(self, item, config):
        return item["key"]

    def run(self, argv=None, config=None):
        config = dict(self.default_config if config is None else config)
        self._engine_keys = set(config["engines"])
        self._selected_engine = None
        return super().run(argv=argv, config=config)

    def open_item(self, item, args, config):
        query = " ".join(args.query)

        if args.selected_engine:
            query = " ".join(args.query[1:])

        if not query:
            return None

        return self.open_url(build_search_url(item, query))

    def open_url(self, url):
        return self.open_location(url)
