import subprocess
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
APP = SourceFileLoader("app", str(REPO_ROOT / "bin" / "app")).load_module()


class AppTests(unittest.TestCase):
    def test_app_name_from_path_removes_app_extension(self):
        self.assertEqual(
            APP.app_name_from_path("/Applications/Safari.app"),
            "Safari",
        )

    @mock.patch("app.shutil.which", return_value="/usr/bin/mdfind")
    @mock.patch("app.subprocess.run")
    def test_discover_apps_uses_mdfind_and_deduplicates_names(self, run, _which):
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="\n".join(
                [
                    "/Applications/Safari.app",
                    "/System/Applications/Calendar.app",
                    "/Users/me/Applications/Safari.app",
                ]
            ),
            stderr="",
        )

        self.assertEqual(APP.discover_apps(), ["Calendar", "Safari"])
        self.assertEqual(
            run.call_args.args[0],
            ["mdfind", 'kMDItemContentType == "com.apple.application-bundle"'],
        )

    def test_resolve_alias_returns_configured_application(self):
        aliases = {
            "browser": "Safari",
            "editor": "Emacs",
        }

        self.assertEqual(APP.resolve_alias("browser", aliases), "Safari")
        self.assertIsNone(APP.resolve_alias("music", aliases))

    def test_filter_apps_matches_case_insensitively(self):
        self.assertEqual(
            APP.filter_apps(["Safari", "Google Chrome", "Calendar"], "chrome"),
            ["Google Chrome"],
        )

    @mock.patch("app.shutil.which", return_value="/usr/bin/fzf")
    @mock.patch("app.subprocess.run")
    def test_choose_app_preserves_duplicate_display_names(self, run, _which):
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="Safari\t#1\n",
            stderr="",
        )

        selected = APP.choose_app(["Calendar", "Safari"], {"fzf_prompt": "app> "})

        self.assertEqual(selected, "Safari")
        self.assertIn("--with-nth=1", run.call_args.args[0])

    @mock.patch("app.shutil.which", return_value="/usr/bin/open")
    @mock.patch("app.subprocess.run")
    def test_open_app_uses_open_a_with_application_name(self, run, _which):
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr="",
        )

        APP.open_app("Safari")

        self.assertEqual(run.call_args.args[0], ["open", "-a", "Safari"])


if __name__ == "__main__":
    unittest.main()
