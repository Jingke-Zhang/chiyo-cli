import os
import subprocess
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock

from chiyo_cli.builtin_tools import go_or_pick as GOP
from chiyo_cli.tool_config import load_tool_config


class GopTests(unittest.TestCase):
    def test_load_config_expands_existing_roots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            root = Path(temp_dir) / "docs"
            root.mkdir()
            config_path.write_text(
                "\n".join(
                    [
                        '["shiori-route/go-or-pick"]',
                        f'roots = ["{root}"]',
                        'exclude = ["Library"]',
                        'fzf_prompt = "gop> "',
                    ]
                ),
                encoding="utf-8",
            )

            config = load_tool_config(
                "shiori-route/go-or-pick",
                GOP.DEFAULT_CONFIG,
                config_path=str(config_path),
            )

            config["roots"] = GOP.normalize_roots(config["roots"])

            self.assertEqual(config["roots"], [str(root)])
            self.assertEqual(config["exclude"], ["Library"])

    @mock.patch("chiyo_cli.builtin_tools.go_or_pick.warn")
    def test_normalize_roots_skips_missing_directories_with_warning(self, warn):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_root = os.path.join(temp_dir, "missing")

            self.assertEqual(GOP.normalize_roots([temp_dir, missing_root]), [temp_dir])
            warn.assert_called_once_with(
                f"skipping missing search root: {missing_root}"
            )

    @mock.patch("chiyo_cli.builtin_tools.go_or_pick.warn")
    def test_normalize_roots_fails_when_no_roots_exist(self, _warn):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_root = os.path.join(temp_dir, "missing")

            with self.assertRaises(RuntimeError):
                GOP.normalize_roots([missing_root])

    @mock.patch("chiyo_cli.toolkit.shutil.which", return_value="/usr/bin/fd")
    @mock.patch("chiyo_cli.toolkit.subprocess.run")
    def test_run_fd_searches_absolute_paths_under_roots(self, run, _which):
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="/Users/me/project\n",
            stderr="",
        )

        self.assertEqual(
            GOP.run_fd("project", ["/Users/me"]),
            ["/Users/me/project"],
        )
        self.assertEqual(
            run.call_args.args[0],
            ["fd", "--absolute-path", "project", "/Users/me"],
        )

    @mock.patch("chiyo_cli.toolkit.shutil.which", return_value="/usr/bin/fd")
    @mock.patch("chiyo_cli.toolkit.subprocess.run")
    def test_run_fd_can_limit_results_for_fast_direct_detection(self, run, _which):
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="/Users/me/project\n/Users/me/project2\n",
            stderr="",
        )

        GOP.run_fd(
            "project",
            ["/Users/me"],
            ["Library", "node_modules"],
            max_results=2,
        )

        self.assertEqual(
            run.call_args.args[0],
            [
                "fd",
                "--absolute-path",
                "--exclude",
                "Library",
                "--exclude",
                "node_modules",
                "--max-results=2",
                "project",
                "/Users/me",
            ],
        )

    def test_compact_path_uses_home_prefix(self):
        home = os.path.expanduser("~")

        self.assertEqual(GOP.compact_path(home), "~")
        self.assertEqual(
            GOP.compact_path(os.path.join(home, "Documents")),
            "~/Documents",
        )

    def test_format_path_choice_styles_paths_by_type_without_type_labels(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "note.txt")
            exec_path = os.path.join(temp_dir, "tool")
            Path(file_path).write_text("note", encoding="utf-8")
            Path(exec_path).write_text("#!/bin/sh\n", encoding="utf-8")
            os.chmod(exec_path, 0o755)

            self.assertIn("\033[1;34m", GOP.format_path_choice(temp_dir))
            self.assertNotIn("\033[1;34m", GOP.format_path_choice(file_path))
            self.assertNotIn("\033[1;32m", GOP.format_path_choice(file_path))
            self.assertIn("\033[1;32m", GOP.format_path_choice(exec_path))
            self.assertNotIn("  dir\t", GOP.format_path_choice(temp_dir))
            self.assertNotIn("  file\t", GOP.format_path_choice(file_path))
            self.assertNotIn("  exec\t", GOP.format_path_choice(exec_path))

    def test_unique_paths_preserves_order_and_removes_duplicates(self):
        self.assertEqual(
            GOP.unique_paths(["/a", "/b", "/a", ""]),
            ["/a", "/b"],
        )

    @mock.patch("chiyo_cli.builtin_tools.go_or_pick.run_fd")
    def test_select_path_returns_single_match_directly_when_allowed(self, choose):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "project")
            choose.return_value = [path]
            selected = GOP.Tool().select_path(
                GOP.Tool().parser().parse_args(["project"]),
                {"roots": [temp_dir], "exclude": [], "fzf_prompt": "gop> "},
            )

        self.assertEqual(selected, path)
        choose.assert_called_once()

    @mock.patch("chiyo_cli.builtin_tools.go_or_pick.choose_path_stream", return_value="/Users/me/project")
    def test_select_path_uses_fzf_when_confirmation_is_required(self, choose):
        with tempfile.TemporaryDirectory() as temp_dir:
            selected = GOP.Tool().select_path(
                GOP.Tool().parser().parse_args(["--confirm", "project"]),
                {"roots": [temp_dir], "exclude": [], "fzf_prompt": "gop> "},
            )

        self.assertEqual(selected, "/Users/me/project")
        choose.assert_called_once()

    @mock.patch("chiyo_cli.builtin_tools.go_or_pick.run_fd")
    def test_list_completions_prints_compact_paths(self, run_fd):
        home = os.path.expanduser("~")
        run_fd.return_value = [
            os.path.join(home, "Documents", "Project"),
            os.path.join(home, "Documents", "Project"),
        ]

        with mock.patch("sys.stdout", new_callable=StringIO) as stdout:
            GOP.Tool().print_completions_for_args(
                GOP.Tool().parser().parse_args(["--list-completions", "Proj"]),
                {"roots": [home], "exclude": ["Library"], "fzf_prompt": "gop> "},
            )

        self.assertEqual(stdout.getvalue(), "~/Documents/Project\n")
        run_fd.assert_called_once_with(
            "Proj",
            [home],
            ["Library"],
            max_results=200,
            fail=mock.ANY,
        )

    @mock.patch("chiyo_cli.toolkit.shutil.which", return_value="/usr/bin/tool")
    @mock.patch("chiyo_cli.builtin_tools.go_or_pick.subprocess.Popen")
    def test_choose_path_stream_formats_fd_output_for_fzf(self, popen, _which):
        fd_process = mock.Mock()
        fd_stdout = mock.MagicMock()
        fd_stdout.__iter__.return_value = iter(["/Users/me/OneDrive - Work/project\n"])
        fd_process.stdout = fd_stdout
        fd_process.wait.return_value = 0
        fzf_process = mock.Mock()
        fzf_process.stdin = mock.Mock()
        fzf_process.stdout.read.return_value = (
            "~/OneDrive - Work/project\t/Users/me/OneDrive - Work/project\t#0\n"
        )
        fzf_process.stderr.read.return_value = ""
        fzf_process.wait.return_value = 0
        popen.side_effect = [fd_process, fzf_process]

        selected = GOP.choose_path_stream(
            "project",
            ["/Users/me"],
            [],
            {"fzf_prompt": "gop> "},
            lambda message: self.fail(message),
        )

        self.assertEqual(selected, "/Users/me/OneDrive - Work/project")
        self.assertEqual(
            popen.call_args_list[0].args[0],
            ["fd", "--absolute-path", "project", "/Users/me"],
        )
        self.assertIn("--with-nth=1", popen.call_args_list[1].args[0])
        self.assertIn("--nth=1", popen.call_args_list[1].args[0])
        written = fzf_process.stdin.write.call_args.args[0]
        self.assertIn("OneDrive - Work", written)
        self.assertIn("/Users/me/OneDrive - Work/project", written)
        self.assertNotIn("\033[8m", written)

    def test_parse_choice_reads_raw_path_column(self):
        self.assertEqual(
            GOP.parse_choice(
                "\033[1;34m~/OneDrive - Work/project\033[0m\t"
                "/Users/me/OneDrive - Work/project\t#0"
            ),
            "/Users/me/OneDrive - Work/project",
        )

    @mock.patch("chiyo_cli.builtin_tools.go_or_pick.run_fd", return_value=["/tmp/project"])
    def test_run_can_override_roots_from_command_line(self, run_fd):
        config = {
            "roots": ["/Users/me"],
            "exclude": [],
            "fzf_prompt": "gop> ",
        }

        result = GOP.Tool().run(
            ["--root", "/tmp", "project"],
            config=config,
            execute_shell_actions=False,
        )

        self.assertEqual(run_fd.call_args.args[1], ["/tmp"])
        self.assertEqual(result.value, "/tmp/project")

    @mock.patch("chiyo_cli.builtin_tools.go_or_pick.run_fd", return_value=["/tmp/project"])
    def test_run_combines_config_and_command_line_excludes(
        self,
        run_fd,
    ):
        config = {
            "roots": ["/tmp"],
            "exclude": ["Library"],
            "fzf_prompt": "gop> ",
        }

        result = GOP.Tool().run(
            ["--exclude", "node_modules", "project"],
            config=config,
            execute_shell_actions=False,
        )

        self.assertEqual(run_fd.call_args.args[2], ["Library", "node_modules"])
        self.assertEqual(result.value, "/tmp/project")


if __name__ == "__main__":
    unittest.main()
