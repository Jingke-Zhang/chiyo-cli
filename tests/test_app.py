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
    def test_discover_apps_uses_mdfind_and_preserves_duplicate_names(self, run, _which):
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

        self.assertEqual(
            APP.discover_apps(),
            [
                {
                    "name": "Calendar",
                    "path": "/System/Applications/Calendar.app",
                },
                {
                    "name": "Safari",
                    "path": "/Applications/Safari.app",
                },
                {
                    "name": "Safari",
                    "path": "/Users/me/Applications/Safari.app",
                },
            ],
        )
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
            APP.filter_apps(
                [
                    {"name": "Safari", "path": "/Applications/Safari.app"},
                    {
                        "name": "Google Chrome",
                        "path": "/Applications/Google Chrome.app",
                    },
                    {"name": "Calendar", "path": "/System/Applications/Calendar.app"},
                ],
                "chrome",
            ),
            [{"name": "Google Chrome", "path": "/Applications/Google Chrome.app"}],
        )

    def test_filter_apps_matches_alias(self):
        self.assertEqual(
            APP.filter_apps(
                [{"name": "Safari", "path": "/Applications/Safari.app"}],
                "browser",
                {"browser": "Safari"},
            ),
            [{"name": "Safari", "path": "/Applications/Safari.app"}],
        )

    def test_format_choice_shows_name_alias_and_path(self):
        choice = APP.format_choice(
            2,
            {"name": "Safari", "path": "/Applications/Safari.app"},
            "browser",
            len("Calendar"),
            len("browser"),
        )

        self.assertEqual(
            choice,
            "Safari    \033[1;32mbrowser\033[0m  "
            "\033[3;4m/Applications/Safari.app\033[0m\t#2",
        )

    def test_format_choice_styles_name_when_alias_is_missing(self):
        choice = APP.format_choice(
            4,
            {"name": "Safari", "path": "/Applications/Safari.app"},
            "",
            len("Calendar"),
            len("browser"),
        )

        self.assertEqual(
            choice,
            "\033[1;32mSafari\033[0m             "
            "\033[3;4m/Applications/Safari.app\033[0m\t#4",
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

        selected = APP.choose_app(
            [
                {"name": "Safari", "path": "/Applications/Safari.app"},
                {"name": "Safari", "path": "/Users/me/Applications/Safari.app"},
            ],
            {
                "fzf_prompt": "app> ",
                "alias": {"browser": "Safari"},
            },
        )

        self.assertEqual(
            selected,
            {"name": "Safari", "path": "/Users/me/Applications/Safari.app"},
        )
        self.assertIn("--ansi", run.call_args.args[0])
        self.assertIn("--with-nth=1", run.call_args.args[0])

    @mock.patch("app.choose_app")
    def test_select_app_returns_single_match_directly_when_allowed(self, choose):
        app = {"name": "Safari", "path": "/Applications/Safari.app"}

        selected = APP.select_app(
            [app],
            {"fzf_prompt": "app> "},
            allow_direct=True,
        )

        self.assertEqual(selected, app)
        choose.assert_not_called()

    @mock.patch("app.choose_app")
    def test_select_app_uses_fzf_for_single_match_without_query(self, choose):
        app = {"name": "Safari", "path": "/Applications/Safari.app"}
        choose.return_value = app

        selected = APP.select_app(
            [app],
            {"fzf_prompt": "app> "},
            allow_direct=False,
        )

        self.assertEqual(selected, app)
        choose.assert_called_once()

    @mock.patch("app.shutil.which", return_value="/usr/bin/open")
    @mock.patch("app.subprocess.run")
    def test_open_app_uses_exact_application_path(self, run, _which):
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr="",
        )

        APP.open_app({"name": "Safari", "path": "/Applications/Safari.app"})

        self.assertEqual(run.call_args.args[0], ["open", "/Applications/Safari.app"])

    @mock.patch("app.shutil.which", return_value="/usr/bin/open")
    @mock.patch("app.subprocess.run")
    def test_open_app_uses_open_a_for_alias_target(self, run, _which):
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr="",
        )

        APP.open_app({"name": "Safari", "path": None})

        self.assertEqual(run.call_args.args[0], ["open", "-a", "Safari"])

    @mock.patch("app.open_app")
    @mock.patch("app.discover_apps")
    @mock.patch("app.load_config")
    def test_main_opens_alias_without_discovery(self, load_config, discover, open_app):
        load_config.return_value = {
            "fzf_prompt": "app> ",
            "alias": {"browser": "Safari"},
        }

        APP.main(["browser"])

        discover.assert_not_called()
        open_app.assert_called_once_with({"name": "Safari", "path": None})


if __name__ == "__main__":
    unittest.main()
