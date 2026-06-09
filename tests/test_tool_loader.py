import tempfile
import unittest
from pathlib import Path

from chiyo_cli.tool_loader import (
    DESCRIPTION_LIMIT,
    ToolLoadError,
    discover_tool_paths,
    discover_builtin_tools,
    discover_tools,
    discover_user_tools,
    load_tool_class,
    load_tool_metadata,
    validate_tool_class,
)
from chiyo_cli.toolkit import PickOpenTool


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "user_tools"


class ToolLoaderTests(unittest.TestCase):
    def test_load_tool_metadata_reads_required_fields(self):
        metadata = load_tool_metadata(FIXTURE_DIR / "paper.py")

        self.assertEqual(metadata.name, "Paper Search")
        self.assertEqual(metadata.command, "paper")
        self.assertEqual(metadata.author, "Fixture Author")
        self.assertEqual(metadata.description, "Search fixture papers and open PDFs.")
        self.assertIn("Search fixture papers", metadata.docs)
        self.assertTrue(metadata.path.endswith("paper.py"))

    def test_load_tool_class_returns_pick_open_tool_subclass(self):
        tool_class = load_tool_class(FIXTURE_DIR / "paper.py")

        self.assertTrue(issubclass(tool_class, PickOpenTool))
        self.assertEqual(tool_class.command, "paper")

    def test_load_tool_metadata_rejects_missing_required_metadata(self):
        with self.assertRaisesRegex(ToolLoadError, "missing author"):
            load_tool_metadata(FIXTURE_DIR / "missing_author.py")

    def test_load_tool_metadata_rejects_framework_reserved_flags(self):
        with self.assertRaisesRegex(ToolLoadError, "--confirm"):
            load_tool_metadata(FIXTURE_DIR / "conflicting_flags.py")

    def test_validate_tool_class_rejects_long_description(self):
        class Tool(PickOpenTool):
            name = "Long Description"
            command = "long-description"
            author = "Fixture Author"
            description = "x" * (DESCRIPTION_LIMIT + 1)
            docs = "Long description."

            def items(self, config):
                return []

            def display_fields(self, item, config):
                return []

            def open_item(self, item, args, config):
                return None

        with self.assertRaisesRegex(ToolLoadError, "description"):
            validate_tool_class(Tool)

    def test_load_tool_class_rejects_missing_tool_class(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "empty.py"
            path.write_text("VALUE = 1\n", encoding="utf-8")

            with self.assertRaisesRegex(ToolLoadError, "no Tool class"):
                load_tool_class(path)

    def test_load_tool_class_rejects_non_pick_open_tool_class(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "wrong.py"
            path.write_text("class Tool:\n    pass\n", encoding="utf-8")

            with self.assertRaisesRegex(ToolLoadError, "subclass PickOpenTool"):
                load_tool_class(path)

    def test_discover_tool_paths_finds_public_python_files(self):
        paths = discover_tool_paths([FIXTURE_DIR, FIXTURE_DIR / "missing"])

        names = [path.name for path in paths]
        self.assertIn("paper.py", names)
        self.assertIn("missing_author.py", names)
        self.assertNotIn("__init__.py", names)

    def test_discover_user_tools_returns_valid_metadata_and_errors(self):
        discovery = discover_user_tools([FIXTURE_DIR])

        commands = [tool.command for tool in discovery.tools]
        self.assertEqual(
            commands,
            ["disabled-notes", "paper"],
        )
        errors_by_name = {
            Path(error.path).name: error.message
            for error in discovery.errors
        }
        self.assertEqual(set(errors_by_name), {"conflicting_flags.py", "missing_author.py"})
        self.assertIn("--confirm", errors_by_name["conflicting_flags.py"])
        self.assertIn("missing author", errors_by_name["missing_author.py"])

    def test_discover_user_tools_ignores_missing_directories(self):
        discovery = discover_user_tools([FIXTURE_DIR / "missing"])

        self.assertEqual(discovery.tools, [])
        self.assertEqual(discovery.errors, [])

    def test_discover_builtin_tools_includes_ws(self):
        discovery = discover_builtin_tools()

        commands = [tool.command for tool in discovery.tools]
        self.assertIn("app", commands)
        self.assertIn("bm", commands)
        self.assertIn("gop", commands)
        self.assertIn("proj", commands)
        self.assertIn("ws", commands)
        self.assertIn("zo", commands)
        self.assertEqual(discovery.errors, [])

    def test_discover_tools_can_include_builtins(self):
        discovery = discover_tools([FIXTURE_DIR], include_builtins=True)

        commands = [tool.command for tool in discovery.tools]
        self.assertIn("paper", commands)
        self.assertIn("ws", commands)


if __name__ == "__main__":
    unittest.main()
