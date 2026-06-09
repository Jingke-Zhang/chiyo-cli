import unittest
from io import StringIO
from unittest import mock

from chiyo_cli.toolkit import (
    Field,
    PickOpenTool,
    STYLE_PRIMARY,
    ToolFlagError,
    tool_argument_flags,
    validate_tool_flags,
)


class MemoryTool(PickOpenTool):
    name = "Memory Tool"
    command = "memory"
    author = "tester"
    description = "Search in-memory test items."
    docs = "Search in-memory test items."
    prompt = "memory> "
    default_config = {"items": []}

    def items(self, config):
        return config["items"]

    def match(self, item, query, config):
        if not query:
            return True

        return query.lower() in item["title"].lower()

    def sort_key(self, item, config):
        return item["rank"]

    def display_fields(self, item, config):
        return [Field(item["title"], STYLE_PRIMARY)]

    def completion_label(self, item, config):
        return item["title"]

    def add_arguments(self, parser):
        parser.add_argument("--print-title", action="store_true")

    def open_item(self, item, args, config):
        if args.print_title:
            print(item["title"])
            return None

        return item


class ConflictingFlagTool(MemoryTool):
    command = "conflicting-memory"

    def add_arguments(self, parser):
        parser.add_argument("--confirm", action="store_true")


class ToolkitTests(unittest.TestCase):
    def test_run_filters_sorts_and_directly_opens_single_query_match(self):
        tool = MemoryTool()
        config = {
            "items": [
                {"title": "Zebra", "rank": 3},
                {"title": "Apple", "rank": 1},
                {"title": "Application", "rank": 2},
            ]
        }

        selected = tool.run(["application"], config)

        self.assertEqual(selected, {"title": "Application", "rank": 2})

    @mock.patch("chiyo_cli.toolkit.choose_item_from")
    def test_run_uses_fzf_when_multiple_items_remain(self, choose_item_from):
        tool = MemoryTool()
        config = {
            "items": [
                {"title": "Zebra", "rank": 3},
                {"title": "Apple", "rank": 1},
            ]
        }
        choose_item_from.return_value = config["items"][1]

        selected = tool.run([], config)

        self.assertEqual(selected, {"title": "Apple", "rank": 1})
        prepared_items = choose_item_from.call_args.args[0]
        self.assertEqual(
            [item["title"] for item in prepared_items],
            ["Apple", "Zebra"],
        )
        self.assertEqual(choose_item_from.call_args.args[1], "memory> ")
        self.assertEqual(
            choose_item_from.call_args.kwargs["search_display_fields"],
            [1],
        )

    def test_run_prints_completions_without_opening(self):
        tool = MemoryTool()
        config = {
            "items": [
                {"title": "Apple", "rank": 1},
                {"title": "Zebra", "rank": 3},
            ]
        }

        with mock.patch("sys.stdout", new_callable=StringIO) as stdout:
            result = tool.run(["--list-completions"], config)

        self.assertIsNone(result)
        self.assertEqual(stdout.getvalue(), "Apple\nZebra\n")

    def test_run_exposes_tool_specific_arguments(self):
        tool = MemoryTool()
        config = {"items": [{"title": "Apple", "rank": 1}]}

        with mock.patch("sys.stdout", new_callable=StringIO) as stdout:
            result = tool.run(["--print-title", "apple"], config)

        self.assertIsNone(result)
        self.assertEqual(stdout.getvalue(), "Apple\n")

    def test_tool_argument_flags_collects_tool_specific_flags(self):
        self.assertEqual(tool_argument_flags(MemoryTool()), {"--print-title"})

    def test_validate_tool_flags_rejects_framework_reserved_flags(self):
        with self.assertRaisesRegex(ToolFlagError, "--confirm"):
            validate_tool_flags(ConflictingFlagTool())

    def test_parser_rejects_framework_reserved_tool_flags(self):
        with self.assertRaisesRegex(ToolFlagError, "--confirm"):
            ConflictingFlagTool().parser()


if __name__ == "__main__":
    unittest.main()
