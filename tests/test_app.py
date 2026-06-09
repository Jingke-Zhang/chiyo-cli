import subprocess
import unittest
from io import StringIO
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

    def test_filter_apps_does_not_match_path_directories(self):
        self.assertEqual(
            APP.filter_apps(
                [
                    {"name": "Safari", "path": "/Applications/Safari.app"},
                    {
                        "name": "Calendar",
                        "path": "/System/Applications/Calendar.app",
                    },
                ],
                "Applications",
            ),
            [],
        )

    def test_app_fields_styles_alias_when_present(self):
        fields = APP.app_fields(
            {"name": "Safari", "path": "/Applications/Safari.app"},
            "browser",
        )

        self.assertEqual(fields[0].style, "")
        self.assertEqual(fields[1].style, "\033[1;32m")
        self.assertEqual(fields[2].style, "\033[3;4m")

    def test_app_fields_styles_name_when_alias_is_missing(self):
        fields = APP.app_fields(
            {"name": "Safari", "path": "/Applications/Safari.app"},
            "",
        )

        self.assertEqual(fields[0].style, "\033[1;32m")
        self.assertEqual(fields[1].style, "")
        self.assertEqual(fields[2].style, "\033[3;4m")

    @mock.patch("app.choose_item")
    def test_choose_app_preserves_duplicate_display_names(self, choose_item):
        apps = [
            {"name": "Safari", "path": "/Applications/Safari.app"},
            {"name": "Safari", "path": "/Users/me/Applications/Safari.app"},
        ]
        choose_item.return_value = apps[1]
        selected = APP.choose_app(
            apps,
            {
                "fzf_prompt": "app> ",
                "alias": {"browser": "Safari"},
            },
        )

        self.assertEqual(
            selected,
            {"name": "Safari", "path": "/Users/me/Applications/Safari.app"},
        )
        self.assertEqual(choose_item.call_args.args[0], apps)

    @mock.patch("app.choose_item")
    def test_choose_app_searches_names_and_aliases_not_paths(self, choose_item):
        apps = [
            {"name": "Safari", "path": "/Applications/Safari.app"},
        ]
        choose_item.return_value = apps[0]

        APP.choose_app(
            apps,
            {
                "fzf_prompt": "app> ",
                "alias": {"browser": "Safari"},
            },
        )

        self.assertEqual(
            choose_item.call_args.kwargs["search_display_fields"],
            [1, 2],
        )
        self.assertNotIn("filter_rows", choose_item.call_args.kwargs)

    def test_list_completions_prints_unique_app_names(self):
        apps = [
            {"name": "Safari", "path": "/Applications/Safari.app"},
            {"name": "Calendar", "path": "/System/Applications/Calendar.app"},
            {"name": "Safari", "path": "/Users/me/Applications/Safari.app"},
        ]

        with mock.patch("sys.stdout", new_callable=StringIO) as stdout:
            APP.list_completions(apps)

        self.assertEqual(stdout.getvalue(), "Safari\nCalendar\n")

    @mock.patch("app.open_app")
    @mock.patch("app.discover_apps")
    @mock.patch("app.load_config")
    def test_main_lists_completions_without_opening_app(
        self,
        load_config,
        discover_apps,
        open_app,
    ):
        load_config.return_value = {"fzf_prompt": "app> ", "alias": {}}
        discover_apps.return_value = [
            {"name": "Safari", "path": "/Applications/Safari.app"},
        ]

        with mock.patch("sys.stdout", new_callable=StringIO) as stdout:
            APP.main(["--list-completions"])

        self.assertEqual(stdout.getvalue(), "Safari\n")
        open_app.assert_not_called()

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

    @mock.patch("app.open_app")
    @mock.patch("app.choose_app")
    @mock.patch("app.discover_apps")
    @mock.patch("app.load_config")
    def test_main_confirms_alias_when_requested(
        self,
        load_config,
        discover,
        choose_app,
        open_app,
    ):
        safari = {"name": "Safari", "path": "/Applications/Safari.app"}
        load_config.return_value = {
            "fzf_prompt": "app> ",
            "alias": {"browser": "Safari"},
        }
        discover.return_value = [safari]
        choose_app.return_value = safari

        APP.main(["--confirm", "browser"])

        discover.assert_called_once()
        choose_app.assert_called_once()
        open_app.assert_called_once_with(safari)


if __name__ == "__main__":
    unittest.main()
