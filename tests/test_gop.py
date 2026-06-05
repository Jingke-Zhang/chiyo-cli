import os
import subprocess
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
GOP = SourceFileLoader("gop_select", str(REPO_ROOT / "bin" / "gop-select")).load_module()


class GopTests(unittest.TestCase):
    def test_load_config_expands_default_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                "\n".join(
                    [
                        "[gop]",
                        'roots = ["~"]',
                        'fzf_prompt = "gop> "',
                    ]
                ),
                encoding="utf-8",
            )

            config = GOP.load_module_config(
                "gop",
                GOP.DEFAULT_CONFIG,
                config_path=str(config_path),
            )

            config["roots"] = [
                os.path.abspath(os.path.expanduser(root))
                for root in config["roots"]
            ]

            self.assertEqual(config["roots"], [os.path.expanduser("~")])

    @mock.patch("gop_select.shutil.which", return_value="/usr/bin/fd")
    @mock.patch("gop_select.subprocess.run")
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

    @mock.patch("gop_select.shutil.which", return_value="/usr/bin/fd")
    @mock.patch("gop_select.subprocess.run")
    def test_run_fd_can_limit_results_for_fast_direct_detection(self, run, _which):
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="/Users/me/project\n/Users/me/project2\n",
            stderr="",
        )

        GOP.run_fd("project", ["/Users/me"], max_results=2)

        self.assertEqual(
            run.call_args.args[0],
            ["fd", "--absolute-path", "--max-results=2", "project", "/Users/me"],
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
            self.assertNotIn("\033[", GOP.format_path_choice(file_path))
            self.assertIn("\033[1;32m", GOP.format_path_choice(exec_path))
            self.assertNotIn("  dir\t", GOP.format_path_choice(temp_dir))
            self.assertNotIn("  file\t", GOP.format_path_choice(file_path))
            self.assertNotIn("  exec\t", GOP.format_path_choice(exec_path))

    def test_unique_paths_preserves_order_and_removes_duplicates(self):
        self.assertEqual(
            GOP.unique_paths(["/a", "/b", "/a", ""]),
            ["/a", "/b"],
        )

    @mock.patch("gop_select.choose_path")
    def test_select_path_returns_single_match_directly_when_allowed(self, choose):
        selected = GOP.select_path(
            ["/Users/me/project"],
            {"fzf_prompt": "gop> "},
            allow_direct=True,
        )

        self.assertEqual(selected, "/Users/me/project")
        choose.assert_not_called()

    @mock.patch("gop_select.choose_path", return_value="/Users/me/project")
    def test_select_path_uses_fzf_when_confirmation_is_required(self, choose):
        selected = GOP.select_path(
            ["/Users/me/project"],
            {"fzf_prompt": "gop> "},
            allow_direct=False,
        )

        self.assertEqual(selected, "/Users/me/project")
        choose.assert_called_once()

    @mock.patch("gop_select.shutil.which", return_value="/usr/bin/tool")
    @mock.patch("gop_select.subprocess.Popen")
    def test_choose_path_stream_formats_fd_output_for_fzf(self, popen, _which):
        fd_process = mock.Mock()
        fd_stdout = mock.MagicMock()
        fd_stdout.__iter__.return_value = iter(["/Users/me/project\n"])
        fd_process.stdout = fd_stdout
        fd_process.wait.return_value = 0
        fzf_process = mock.Mock()
        fzf_process.stdin = mock.Mock()
        fzf_process.stdout.read.return_value = "project\t/Users/me/project\n"
        fzf_process.stderr.read.return_value = ""
        fzf_process.wait.return_value = 0
        popen.side_effect = [fd_process, fzf_process]

        selected = GOP.choose_path_stream(
            "project",
            ["/Users/me"],
            {"fzf_prompt": "gop> "},
        )

        self.assertEqual(selected, "/Users/me/project")
        self.assertEqual(
            popen.call_args_list[0].args[0],
            ["fd", "--absolute-path", "project", "/Users/me"],
        )
        self.assertIn("/Users/me/project", fzf_process.stdin.write.call_args.args[0])
        self.assertIn("\t/Users/me/project", fzf_process.stdin.write.call_args.args[0])

    @mock.patch("builtins.print")
    @mock.patch("gop_select.run_fd", return_value=["/tmp/project"])
    @mock.patch("gop_select.load_config")
    def test_main_can_override_roots_from_command_line(self, load_config, run_fd, print_):
        load_config.return_value = {
            "roots": ["/Users/me"],
            "fzf_prompt": "gop> ",
        }

        GOP.main(["--root", "/tmp", "project"])

        self.assertEqual(run_fd.call_args.args[1], ["/tmp"])
        print_.assert_called_once_with("/tmp/project")


if __name__ == "__main__":
    unittest.main()
