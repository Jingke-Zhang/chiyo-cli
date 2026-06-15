import json
import unittest
from io import StringIO
from unittest import mock

from chiyo_cli.builtin_tools import gtd as GTD
from chiyo_cli.toolkit import ShellAction


AGENDA_ITEM = {
    "todo": "TODO",
    "title": "Write release notes",
    "agenda": "todo: TODO Write release notes",
    "category": "chiyo",
    "file": "/tmp/chiyo/tasks.org",
    "line": 42,
    "column": 3,
}


class GtdTests(unittest.TestCase):
    def test_agenda_items_expression_includes_configured_span_and_start_day(self):
        expression = GTD.agenda_items_expression(
            {
                "agenda_span": "week",
                "agenda_start_day": "+1d",
            }
        )

        self.assertIn("(org-agenda-span 'week)", expression)
        self.assertIn('(org-agenda-start-day "+1d")', expression)

    def test_agenda_items_expression_treats_empty_start_day_as_org_default(self):
        expression = GTD.agenda_items_expression(GTD.DEFAULT_CONFIG)

        self.assertIn("(org-agenda-span 'day)", expression)
        self.assertIn("(org-agenda-start-day nil)", expression)

    def test_parse_emacs_json_accepts_emacs_printed_string(self):
        payload = json.dumps([AGENDA_ITEM])
        stdout = json.dumps(payload) + "\n"

        self.assertEqual(GTD.parse_emacs_json(stdout), [AGENDA_ITEM])

    def test_parse_emacs_json_accepts_raw_json(self):
        self.assertEqual(
            GTD.parse_emacs_json(json.dumps([AGENDA_ITEM])),
            [AGENDA_ITEM],
        )

    def test_items_reads_agenda_items_from_emacsclient(self):
        with mock.patch("chiyo_cli.builtin_tools.gtd.run_emacsclient_eval") as run:
            run.return_value = json.dumps(json.dumps([AGENDA_ITEM]))

            items = GTD.Tool().items(GTD.DEFAULT_CONFIG)

        self.assertEqual(items, [AGENDA_ITEM])
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0], "emacsclient")

    def test_match_searches_agenda_item_fields(self):
        self.assertTrue(GTD.Tool().match(AGENDA_ITEM, "todo release", {}))
        self.assertTrue(GTD.Tool().match(AGENDA_ITEM, "chiyo tasks", {}))
        self.assertFalse(GTD.Tool().match(AGENDA_ITEM, "meeting", {}))

    def test_display_fields_show_task_and_location(self):
        fields = GTD.Tool().display_fields(AGENDA_ITEM, {})

        self.assertEqual([field.value for field in fields], [
            "TODO",
            "Write release notes",
            "chiyo",
            "/tmp/chiyo/tasks.org:42",
        ])

    def test_run_prints_elisp_without_emacsclient(self):
        with mock.patch("sys.stdout", new_callable=StringIO) as stdout:
            result = GTD.Tool().run(
                ["--print-elisp"],
                config=GTD.DEFAULT_CONFIG,
            )

        self.assertIn("org-agenda-list", result)
        self.assertIn("org-marker", result)
        self.assertEqual(stdout.getvalue(), result + "\n")

    def test_run_opens_selected_agenda_item(self):
        with (
            mock.patch("chiyo_cli.builtin_tools.gtd.agenda_items", return_value=[AGENDA_ITEM]),
            mock.patch("chiyo_cli.builtin_tools.gtd.require_command"),
        ):
            result = GTD.Tool().run(
                ["release"],
                config=GTD.DEFAULT_CONFIG,
                execute_shell_actions=False,
            )

        self.assertEqual(
            result,
            ShellAction.command(["emacsclient", "-n", "+42:3", "/tmp/chiyo/tasks.org"]),
        )

    @mock.patch("chiyo_cli.builtin_tools.gtd.require_command")
    @mock.patch("chiyo_cli.builtin_tools.gtd.subprocess.run")
    def test_run_emacsclient_eval_returns_stdout(self, run, require_command):
        run.return_value = mock.Mock(returncode=0, stdout='"[]"\n', stderr="")

        self.assertEqual(
            GTD.run_emacsclient_eval("emacsclient", "(json-encode [])"),
            '"[]"\n',
        )
        require_command.assert_called_once_with("emacsclient")
        run.assert_called_once_with(
            ["emacsclient", "-e", "(json-encode [])"],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_emacsclient_open_command_jumps_to_file_location(self):
        self.assertEqual(
            ["emacsclient", "-n", "+42:3", "/tmp/chiyo/tasks.org"],
            GTD.emacsclient_open_command("emacsclient", AGENDA_ITEM),
        )

    def test_emacsclient_open_command_allows_terminal_emacsclient(self):
        self.assertEqual(
            ["emacsclient", "-nw", "+42:3", "/tmp/chiyo/tasks.org"],
            GTD.emacsclient_open_command("emacsclient", AGENDA_ITEM, ["-nw"]),
        )


if __name__ == "__main__":
    unittest.main()
