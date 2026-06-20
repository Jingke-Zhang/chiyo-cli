import unittest
from pathlib import Path

from chiyo_cli.tool_config import DEFAULT_CHIYO_CONFIG
from chiyo_cli.tool_loader import discover_builtin_tools


REPO_ROOT = Path(__file__).resolve().parents[1]


def read_doc(path):
    return (REPO_ROOT / path).read_text(encoding="utf-8")


class DocsConsistencyTests(unittest.TestCase):
    def test_readme_lists_every_builtin_tool_doc(self):
        readme = read_doc("README.md")
        expected_docs = {
            "app": "docs/app.md",
            "bm": "docs/bm.md",
            "agd": "docs/agd.md",
            "gop": "docs/gop.md",
            "proj": "docs/proj.md",
            "s": "docs/s.md",
            "ws": "docs/workspace.md",
            "zo": "docs/zo.md",
        }

        for tool in discover_builtin_tools().tools:
            with self.subTest(tool=tool.cmd):
                self.assertIn(f"[`{tool.cmd}`]({expected_docs[tool.cmd]})", readme)

    def test_default_enabled_tools_are_documented(self):
        readme = read_doc("README.md")
        chiyo_doc = read_doc("docs/chiyo.md")

        for tool_key in DEFAULT_CHIYO_CONFIG["enabled_tools"]:
            with self.subTest(tool=tool_key):
                self.assertIn(tool_key, readme)
                self.assertIn(tool_key, chiyo_doc)

    def test_dashboard_is_documented(self):
        readme = read_doc("README.md")
        chiyo_doc = read_doc("docs/chiyo.md")
        design_doc = read_doc("docs/user-tools-design.md")

        self.assertIn("dashboard", readme)
        self.assertIn("chiyo", readme)
        self.assertIn("show a compact local dashboard", chiyo_doc)
        self.assertIn("shows a compact dashboard", design_doc)
        self.assertNotIn("future version may open an `fzf`", design_doc)

    def test_install_docs_use_multi_tool_forms(self):
        install_doc = read_doc("docs/install.md")
        chiyo_doc = read_doc("docs/chiyo.md")

        self.assertIn("chiyo install TOOLS...", install_doc)
        self.assertIn("chiyo uninstall TOOLS...", install_doc)
        self.assertIn("install TOOLS...", chiyo_doc)
        self.assertIn("uninstall TOOLS...", chiyo_doc)
        self.assertNotIn("chiyo install TOOL`", install_doc)

    def test_design_doc_no_longer_presents_builtin_migration_as_pending(self):
        design_doc = read_doc("docs/user-tools-design.md")

        self.assertIn("## Historical Implementation Plan", design_doc)
        self.assertIn("Moved simple built-ins", design_doc)
        self.assertIn("## Built-In Regression Criteria", design_doc)
        self.assertNotIn("Migrate one simple built-in", design_doc)
        self.assertNotIn("during migration", design_doc)


if __name__ == "__main__":
    unittest.main()
