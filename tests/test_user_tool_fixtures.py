import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

from chiyo_cli.toolkit import PickOpenTool


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "user_tools"


def load_fixture(name):
    path = FIXTURE_DIR / f"{name}.py"
    return SourceFileLoader(f"fixture_{name}", str(path)).load_module()


class UserToolFixtureTests(unittest.TestCase):
    def test_valid_paper_fixture_defines_tool_class(self):
        module = load_fixture("paper")

        self.assertTrue(issubclass(module.Tool, PickOpenTool))
        self.assertEqual(module.Tool.cmd, "paper")
        self.assertEqual(module.Tool.name, "Paper Search")
        self.assertEqual(module.Tool.author, "Fixture Author")

    def test_valid_paper_fixture_uses_convenience_api(self):
        module = load_fixture("paper")
        tool = module.Tool()

        fields = tool.display_fields(
            {"title": "Paper", "path": "/tmp/Paper.pdf"},
            {},
        )

        self.assertEqual([field.value for field in fields], ["Paper", "/tmp/Paper.pdf"])

    def test_invalid_metadata_fixture_is_available_for_validation_tests(self):
        module = load_fixture("missing_author")

        self.assertTrue(issubclass(module.Tool, PickOpenTool))
        self.assertEqual(module.Tool.cmd, "missing-author")
        self.assertIsNone(module.Tool.author)

    def test_disabled_fixture_is_valid_but_not_enabled_by_default(self):
        module = load_fixture("disabled_notes")

        self.assertTrue(issubclass(module.Tool, PickOpenTool))
        self.assertEqual(module.Tool.cmd, "disabled-notes")
        self.assertEqual(module.Tool.description, "Fixture tool used for disabled-tool tests.")

    def test_conflicting_flags_fixture_is_available_for_flag_validation_tests(self):
        module = load_fixture("conflicting_flags")

        self.assertTrue(issubclass(module.Tool, PickOpenTool))
        self.assertEqual(module.Tool.cmd, "conflicting-flags")


if __name__ == "__main__":
    unittest.main()
