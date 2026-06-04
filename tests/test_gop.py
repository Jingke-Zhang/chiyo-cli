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

    def test_compact_path_uses_home_prefix(self):
        home = os.path.expanduser("~")

        self.assertEqual(GOP.compact_path(home), "~")
        self.assertEqual(
            GOP.compact_path(os.path.join(home, "Documents")),
            "~/Documents",
        )

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


if __name__ == "__main__":
    unittest.main()
