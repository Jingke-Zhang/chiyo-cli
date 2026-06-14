import os
import subprocess
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock

from chiyo_cli.builtin_tools import proj as PROJ
from chiyo_cli.tool_config import load_tool_config


class ProjTests(unittest.TestCase):
    def test_load_config_preserves_custom_markers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                "\n".join(
                    [
                        '["jingke-zhang/project"]',
                        f'roots = ["{temp_dir}"]',
                        'markers = [".project", "package.json"]',
                        'exclude = ["node_modules"]',
                        'fzf_prompt = "proj> "',
                    ]
                ),
                encoding="utf-8",
            )

            config = load_tool_config(
                "jingke-zhang/project",
                PROJ.DEFAULT_CONFIG,
                config_path=str(config_path),
            )

            self.assertEqual(config["markers"], [".project", "package.json"])

    def test_project_from_marker_returns_parent_directory(self):
        self.assertEqual(
            PROJ.project_from_marker("/Users/me/project/.project"),
            "/Users/me/project",
        )

    @mock.patch("chiyo_cli.builtin_tools.proj.warn")
    def test_normalize_roots_skips_missing_directories_with_warning(self, warn):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_root = os.path.join(temp_dir, "missing")

            self.assertEqual(PROJ.normalize_roots([temp_dir, missing_root]), [temp_dir])
            warn.assert_called_once_with(
                f"skipping missing project root: {missing_root}"
            )

    @mock.patch("chiyo_cli.toolkit.shutil.which", return_value="/usr/bin/fd")
    @mock.patch("chiyo_cli.toolkit.subprocess.run")
    def test_run_fd_searches_project_markers(self, run, _which):
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="/Users/me/project/.project\n",
            stderr="",
        )

        self.assertEqual(
            PROJ.run_fd(["/Users/me"], [".project", ".git"], ["node_modules"]),
            ["/Users/me/project/.project"],
        )
        self.assertEqual(
            run.call_args.args[0],
            [
                "fd",
                "--absolute-path",
                "--hidden",
                "--exclude",
                "node_modules",
                "^(\\.project|\\.git)$",
                "/Users/me",
            ],
        )

    @mock.patch("chiyo_cli.builtin_tools.proj.run_fd")
    def test_all_projects_deduplicates_project_paths(self, run_fd):
        run_fd.return_value = [
            "/Users/me/project/.project",
            "/Users/me/project/.git",
        ]

        self.assertEqual(
            PROJ.all_projects(["/Users/me"], [".project", ".git"], [], lambda message: self.fail(message)),
            ["/Users/me/project"],
        )

    def test_filter_projects_matches_only_project_name(self):
        projects = [
            "/Users/me/Documents/chiyo-cli",
            "/Users/me/special-path/other",
        ]

        self.assertEqual(
            PROJ.filter_projects(projects, "chiyo"),
            ["/Users/me/Documents/chiyo-cli"],
        )
        self.assertEqual(PROJ.filter_projects(projects, "special-path"), [])

    def test_project_widths_uses_display_width(self):
        self.assertEqual(
            PROJ.project_widths(["/tmp/a", "/tmp/長い"]),
            [4],
        )

    def test_project_fields_separates_name_and_path(self):
        path = os.path.join(os.path.expanduser("~"), "Documents", "chiyo-cli")

        fields = PROJ.project_fields(
            path,
            [9],
        )

        self.assertEqual(fields[0].value, "chiyo-cli  ")
        self.assertEqual(fields[1].value, "~/Documents/chiyo-cli")

    @mock.patch("chiyo_cli.fzf.choose_item")
    def test_choose_project_searches_only_project_name_column(self, choose_item):
        choose_item.return_value = "/Users/me/Documents/chiyo-cli"

        tool = PROJ.Tool()
        selected = tool.select_item(
            ["/Users/me/Documents/chiyo-cli"],
            "",
            tool.parser().parse_args([]),
            {"fzf_prompt": "proj> "},
        )

        self.assertEqual(selected, "/Users/me/Documents/chiyo-cli")
        self.assertEqual(choose_item.call_args.args[0], ["/Users/me/Documents/chiyo-cli"])
        self.assertEqual(choose_item.call_args.kwargs["search_display_fields"], [1])
        self.assertNotIn("filter_rows", choose_item.call_args.kwargs)

    @mock.patch("chiyo_cli.fzf.choose_item")
    def test_select_project_returns_single_match_directly_when_allowed(self, choose):
        tool = PROJ.Tool()
        selected = tool.select_item(
            ["/Users/me/project"],
            "project",
            tool.parser().parse_args(["project"]),
            {"fzf_prompt": "proj> "},
        )

        self.assertEqual(selected, "/Users/me/project")
        choose.assert_not_called()

    def test_list_completions_prints_project_names(self):
        with mock.patch("sys.stdout", new_callable=StringIO) as stdout:
            tool = PROJ.Tool()
            with mock.patch.object(
                tool,
                "items",
                return_value=[
                    "/Users/me/chiyo-cli",
                    "/Users/me/other",
                ],
            ):
                tool.print_completions({})

        self.assertEqual(stdout.getvalue(), "chiyo-cli\nother\n")


if __name__ == "__main__":
    unittest.main()
