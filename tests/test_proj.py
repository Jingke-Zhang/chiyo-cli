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
    def test_load_config_preserves_custom_markers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                "\n".join(
                    [
                        "[proj]",
                        f'roots = ["{temp_dir}"]',
                        'markers = [".project", "package.json"]',
                        'exclude = ["node_modules"]',
                        'fzf_prompt = "proj> "',
                    ]
                ),
                encoding="utf-8",
            )

            config = PROJ.load_module_config(
                "proj",
                PROJ.DEFAULT_CONFIG,
                config_path=str(config_path),
            )

            self.assertEqual(config["markers"], [".project", "package.json"])

    def test_project_from_marker_returns_parent_directory(self):
        self.assertEqual(
            PROJ.project_from_marker("/Users/me/project/.project"),
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

    @mock.patch("proj_select.run_fd")
    def test_all_projects_deduplicates_project_paths(self, run_fd):
        run_fd.return_value = [
            "/Users/me/project/.project",
            "/Users/me/project/.git",
        ]

        self.assertEqual(
            PROJ.all_projects(["/Users/me"], [".project", ".git"], []),
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

    @mock.patch("proj_select.choose_item")
    def test_choose_project_searches_only_project_name_column(self, choose_item):
        choose_item.return_value = "/Users/me/Documents/chiyo-cli"

        selected = PROJ.choose_project(
            ["/Users/me/Documents/chiyo-cli"],
            {"fzf_prompt": "proj> "},
        )

        self.assertEqual(selected, "/Users/me/Documents/chiyo-cli")
        self.assertEqual(choose_item.call_args.args[0], ["/Users/me/Documents/chiyo-cli"])
        self.assertEqual(
            choose_item.call_args.kwargs["filter_rows"],
            [["chiyo-cli"]],
        )

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
