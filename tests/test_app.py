import subprocess
import unittest
from io import StringIO
from unittest import mock

from chiyo_cli.builtin_tools import app as APP


class AppTests(unittest.TestCase):
    def test_app_name_from_path_removes_app_extension(self):
        self.assertEqual(
            APP.app_name_from_path("/Applications/Safari.app"),
            "Safari",
        )

    @mock.patch("chiyo_cli.toolkit.shutil.which", return_value="/usr/bin/mdfind")
    @mock.patch("chiyo_cli.toolkit.subprocess.run")
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
            APP.discover_apps(lambda message: self.fail(message)),
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
            [
                app
                for app in [
                    {"name": "Safari", "path": "/Applications/Safari.app"},
                    {
                        "name": "Google Chrome",
                        "path": "/Applications/Google Chrome.app",
                    },
                    {"name": "Calendar", "path": "/System/Applications/Calendar.app"},
                ]
                if APP.Tool().match(app, "chrome", {"alias": {}})
            ],
            [{"name": "Google Chrome", "path": "/Applications/Google Chrome.app"}],
        )

    def test_filter_apps_matches_alias(self):
        self.assertEqual(
            [
                app
                for app in [{"name": "Safari", "path": "/Applications/Safari.app"}]
                if APP.Tool().match(app, "browser", {"alias": {"browser": "Safari"}})
            ],
            [{"name": "Safari", "path": "/Applications/Safari.app"}],
        )

    def test_filter_apps_does_not_match_path_directories(self):
        self.assertEqual(
            [
                app
                for app in [
                    {"name": "Safari", "path": "/Applications/Safari.app"},
                    {
                        "name": "Calendar",
                        "path": "/System/Applications/Calendar.app",
                    },
                ]
                if APP.Tool().match(app, "Applications", {"alias": {}})
            ],
            [],
        )

    def test_app_fields_styles_alias_when_present(self):
        fields = APP.Tool().display_fields(
            {"name": "Safari", "path": "/Applications/Safari.app"},
            {"alias": {"browser": "Safari"}},
        )

        self.assertEqual(fields[0].style, "")
        self.assertEqual(fields[1].style, "\033[1;32m")
        self.assertEqual(fields[2].style, "\033[3;4m")

    def test_app_fields_styles_name_when_alias_is_missing(self):
        fields = APP.Tool().display_fields(
            {"name": "Safari", "path": "/Applications/Safari.app"},
            {"alias": {}},
        )

        self.assertEqual(fields[0].style, "\033[1;32m")
        self.assertEqual(fields[1].style, "")
        self.assertEqual(fields[2].style, "\033[3;4m")

    @mock.patch("chiyo_cli.toolkit.choose_item_from")
    def test_choose_app_preserves_duplicate_display_names(self, choose_item_from):
        apps = [
            {"name": "Safari", "path": "/Applications/Safari.app"},
            {"name": "Safari", "path": "/Users/me/Applications/Safari.app"},
        ]
        choose_item_from.return_value = apps[1]
        selected = APP.Tool().select_item(
            apps,
            "",
            APP.Tool().parser().parse_args([]),
            {"fzf_prompt": "app> ", "alias": {"browser": "Safari"}},
        )

        self.assertEqual(
            selected,
            {"name": "Safari", "path": "/Users/me/Applications/Safari.app"},
        )
        self.assertEqual(choose_item_from.call_args.args[0], apps)

    @mock.patch("chiyo_cli.toolkit.choose_item_from")
    def test_choose_app_uses_python_display_and_searches_visible_name_fields(
        self,
        choose_item_from,
    ):
        apps = [
            {"name": "Safari", "path": "/Applications/Safari.app"},
        ]
        choose_item_from.return_value = apps[0]

        APP.Tool().select_item(
            apps,
            "",
            APP.Tool().parser().parse_args([]),
            {"fzf_prompt": "app> ", "alias": {"browser": "Safari"}},
        )

        self.assertEqual(
            choose_item_from.call_args.kwargs["search_display_fields"],
            [1, 2],
        )
        self.assertNotIn("filter_rows", choose_item_from.call_args.kwargs)
        display_fields = choose_item_from.call_args.kwargs["display_fields"]
        fields = display_fields(apps[0])

        self.assertEqual(fields[0].value, "Safari")
        self.assertEqual(fields[0].style, "")
        self.assertEqual(fields[1].value, "browser")
        self.assertEqual(fields[1].style, "\033[1;32m")

    def test_list_completions_prints_unique_app_names(self):
        apps = [
            {"name": "Safari", "path": "/Applications/Safari.app"},
            {"name": "Calendar", "path": "/System/Applications/Calendar.app"},
            {"name": "Safari", "path": "/Users/me/Applications/Safari.app"},
        ]

        with mock.patch("sys.stdout", new_callable=StringIO) as stdout:
            tool = APP.Tool()
            with mock.patch.object(tool, "items", return_value=apps):
                tool.print_completions({"alias": {}})

        self.assertEqual(stdout.getvalue(), "Safari\nCalendar\n")

    @mock.patch("chiyo_cli.builtin_tools.app.open_app")
    def test_run_lists_completions_without_opening_app(self, open_app):
        tool = APP.Tool()

        with mock.patch.object(tool, "items", return_value=[
            {"name": "Safari", "path": "/Applications/Safari.app"},
        ]):
            with mock.patch("sys.stdout", new_callable=StringIO) as stdout:
                tool.run(["--list-completions"], config={"fzf_prompt": "app> ", "alias": {}})

        self.assertEqual(stdout.getvalue(), "Safari\n")
        open_app.assert_not_called()

    @mock.patch("chiyo_cli.toolkit.choose_item_from")
    def test_select_app_returns_single_match_directly_when_allowed(self, choose):
        app = {"name": "Safari", "path": "/Applications/Safari.app"}

        selected = APP.Tool().select_item(
            [app],
            "Safari",
            APP.Tool().parser().parse_args(["Safari"]),
            {"fzf_prompt": "app> ", "alias": {}},
        )

        self.assertEqual(selected, app)
        choose.assert_not_called()

    @mock.patch("chiyo_cli.toolkit.choose_item_from")
    def test_select_app_uses_fzf_for_single_match_without_query(self, choose):
        app = {"name": "Safari", "path": "/Applications/Safari.app"}
        choose.return_value = app

        selected = APP.Tool().select_item(
            [app],
            "",
            APP.Tool().parser().parse_args([]),
            {"fzf_prompt": "app> ", "alias": {}},
        )

        self.assertEqual(selected, app)
        choose.assert_called_once()

    @mock.patch("chiyo_cli.toolkit.shutil.which", return_value="/usr/bin/open")
    @mock.patch("chiyo_cli.toolkit.subprocess.run")
    def test_open_app_uses_exact_application_path(self, run, _which):
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr="",
        )

        APP.open_app({"name": "Safari", "path": "/Applications/Safari.app"}, lambda message: self.fail(message))

        self.assertEqual(run.call_args.args[0], ["open", "/Applications/Safari.app"])

    @mock.patch("chiyo_cli.toolkit.shutil.which", return_value="/usr/bin/open")
    @mock.patch("chiyo_cli.toolkit.subprocess.run")
    def test_open_app_uses_open_a_for_alias_target(self, run, _which):
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr="",
        )

        APP.open_app({"name": "Safari", "path": None}, lambda message: self.fail(message))

        self.assertEqual(run.call_args.args[0], ["open", "-a", "Safari"])

    @mock.patch("chiyo_cli.builtin_tools.app.open_app")
    @mock.patch("chiyo_cli.builtin_tools.app.discover_apps")
    def test_run_opens_alias_without_discovery(self, discover, open_app):
        config = {
            "fzf_prompt": "app> ",
            "alias": {"browser": "Safari"},
        }

        APP.Tool().run(["browser"], config=config)

        discover.assert_not_called()
        open_app.assert_called_once()

    @mock.patch("chiyo_cli.builtin_tools.app.open_app")
    @mock.patch("chiyo_cli.toolkit.choose_item_from")
    def test_run_confirms_alias_when_requested(
        self,
        choose_item,
        open_app,
    ):
        safari = {"name": "Safari", "path": "/Applications/Safari.app"}
        config = {
            "fzf_prompt": "app> ",
            "alias": {"browser": "Safari"},
        }
        choose_item.return_value = safari

        tool = APP.Tool()
        with mock.patch.object(tool, "items", return_value=[safari]):
            tool.run(["--confirm", "browser"], config=config)

        choose_item.assert_called_once()
        open_app.assert_called_once()


if __name__ == "__main__":
    unittest.main()
