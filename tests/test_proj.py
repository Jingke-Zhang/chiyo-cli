import os
import subprocess
import tempfile
import unittest
from io import StringIO
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
PROJ = SourceFileLoader("proj_select", str(REPO_ROOT / "bin" / "proj-select")).load_module()


class ProjTests(unittest.TestCase):
    def test_project_from_git_dir_returns_parent_directory(self):
        self.assertEqual(
            PROJ.project_from_git_dir("/Users/me/project/.git"),
            "/Users/me/project",
        )

    @mock.patch("proj_select.warn")
    def test_normalize_roots_skips_missing_directories_with_warning(self, warn):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_root = os.path.join(temp_dir, "missing")

            self.assertEqual(PROJ.normalize_roots([temp_dir, missing_root]), [temp_dir])
            warn.assert_called_once_with(
                f"skipping missing project root: {missing_root}"
            )

    @mock.patch("proj_select.shutil.which", return_value="/usr/bin/fd")
    @mock.patch("proj_select.subprocess.run")
    def test_run_fd_searches_git_directories(self, run, _which):
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="/Users/me/project/.git\n",
            stderr="",
        )

        self.assertEqual(
            PROJ.run_fd(["/Users/me"], ["node_modules"]),
            ["/Users/me/project/.git"],
        )
        self.assertEqual(
            run.call_args.args[0],
            [
                "fd",
                "--absolute-path",
                "--hidden",
                "--type",
                "d",
                "--exclude",
                "node_modules",
                "^\\.git$",
                "/Users/me",
            ],
        )

    @mock.patch("proj_select.run_fd")
    def test_all_projects_deduplicates_project_paths(self, run_fd):
        run_fd.return_value = [
            "/Users/me/project/.git",
            "/Users/me/project/.git",
        ]

        self.assertEqual(
            PROJ.all_projects(["/Users/me"], []),
            ["/Users/me/project"],
        )

    def test_filter_projects_matches_name_or_compact_path(self):
        projects = [
            "/Users/me/Documents/chiyo-cli",
            "/Users/me/Projects/other",
        ]

        self.assertEqual(
            PROJ.filter_projects(projects, "chiyo"),
            ["/Users/me/Documents/chiyo-cli"],
        )

    def test_format_project_choice_hides_exact_path_in_last_column(self):
        choice = PROJ.format_project_choice("/Users/me/Documents/chiyo-cli")

        self.assertIn("chiyo-cli", choice)
        self.assertTrue(choice.endswith("\t/Users/me/Documents/chiyo-cli"))

    @mock.patch("proj_select.choose_project")
    def test_select_project_returns_single_match_directly_when_allowed(self, choose):
        selected = PROJ.select_project(
            ["/Users/me/project"],
            {"fzf_prompt": "proj> "},
            allow_direct=True,
        )

        self.assertEqual(selected, "/Users/me/project")
        choose.assert_not_called()

    def test_list_completions_prints_project_names(self):
        with mock.patch("sys.stdout", new_callable=StringIO) as stdout:
            PROJ.list_completions(
                [
                    "/Users/me/chiyo-cli",
                    "/Users/me/other",
                ]
            )

        self.assertEqual(stdout.getvalue(), "chiyo-cli\nother\n")


if __name__ == "__main__":
    unittest.main()
