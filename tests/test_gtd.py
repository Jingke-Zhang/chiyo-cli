import json
import os
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
INBOX_PATH = os.path.expanduser("~/org/inbox.org")


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

    def test_view_expression_can_use_agenda_dispatch_key(self):
        expression = GTD.view_expression(GTD.DEFAULT_CONFIG, "todo")

        self.assertIn('(org-agenda nil "t")', expression)
        self.assertIn("org-marker", expression)

    def test_view_expression_can_use_emacs_function(self):
        config = dict(GTD.DEFAULT_CONFIG)
        config["views"] = {
            "next": {
                "name": "Next Actions",
                "function": "my/gtd-next-actions",
            }
        }

        expression = GTD.view_expression(config, "next")

        self.assertIn("(funcall 'my/gtd-next-actions)", expression)

    def test_view_expression_rejects_invalid_emacs_function_name(self):
        config = dict(GTD.DEFAULT_CONFIG)
        config["views"] = {
            "bad": {
                "name": "Bad",
                "function": "(delete-file \"x\")",
            }
        }

        with self.assertRaises(GTD.ToolError):
            GTD.view_expression(config, "bad")

    def test_capture_expression_appends_todo_to_inbox(self):
        expression = GTD.capture_expression(GTD.DEFAULT_CONFIG, 'Read "paper"')

        self.assertIn('(expand-file-name "~/org/inbox.org")', expression)
        self.assertIn('"Read \\"paper\\""', expression)
        self.assertIn('(insert "* TODO " title "\\n")', expression)
        self.assertIn(":CREATED:", expression)

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

    def test_run_capture_prints_elisp_without_emacsclient(self):
        with mock.patch("sys.stdout", new_callable=StringIO) as stdout:
            result = GTD.Tool().run(
                ["--print-elisp", "capture", "read", "paper"],
                config=GTD.DEFAULT_CONFIG,
            )

        self.assertIn("find-file-noselect", result)
        self.assertIn('"read paper"', result)
        self.assertEqual(stdout.getvalue(), result + "\n")

    def test_run_view_prints_elisp_without_emacsclient(self):
        with mock.patch("sys.stdout", new_callable=StringIO) as stdout:
            result = GTD.Tool().run(
                ["--print-elisp", "view", "todo"],
                config=GTD.DEFAULT_CONFIG,
            )

        self.assertIn('(org-agenda nil "t")', result)
        self.assertEqual(stdout.getvalue(), result + "\n")

    def test_run_capture_requires_text(self):
        with self.assertRaises(SystemExit):
            GTD.Tool().run(["capture"], config=GTD.DEFAULT_CONFIG)

    def test_run_capture_calls_emacsclient(self):
        with mock.patch("chiyo_cli.builtin_tools.gtd.run_emacsclient_eval") as run:
            result = GTD.Tool().run(
                ["capture", "read", "paper"],
                config=GTD.DEFAULT_CONFIG,
            )

        self.assertIsNone(result)
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0], "emacsclient")
        self.assertIn('"read paper"', run.call_args.args[1])

    def test_file_item_reads_configured_alias(self):
        self.assertEqual(
            GTD.file_item(GTD.DEFAULT_CONFIG, "inbox"),
            {
                "file": INBOX_PATH,
                "line": 1,
                "column": 1,
            },
        )

    def test_run_open_file_alias(self):
        with mock.patch("chiyo_cli.builtin_tools.gtd.require_command"):
            result = GTD.Tool().run(
                ["open", "inbox"],
                config=GTD.DEFAULT_CONFIG,
                execute_shell_actions=False,
            )

        self.assertEqual(
            result,
            ShellAction.command(["emacsclient", "-n", "+1:1", INBOX_PATH]),
        )

    def test_run_open_file_alias_uses_configured_terminal_args(self):
        config = dict(GTD.DEFAULT_CONFIG)
        config["emacsclient_open_args"] = ["-nw"]

        with mock.patch("chiyo_cli.builtin_tools.gtd.require_command"):
            result = GTD.Tool().run(
                ["open", "inbox"],
                config=config,
                execute_shell_actions=False,
            )

        self.assertEqual(
            result,
            ShellAction.command(["emacsclient", "-nw", "+1:1", INBOX_PATH]),
        )

    def test_run_bare_file_alias_only_when_enabled(self):
        with mock.patch("chiyo_cli.builtin_tools.gtd.require_command"):
            result = GTD.Tool().run(
                ["inbox"],
                config=GTD.DEFAULT_CONFIG,
                execute_shell_actions=False,
            )

        self.assertEqual(
            result,
            ShellAction.command(["emacsclient", "-n", "+1:1", INBOX_PATH]),
        )

    def test_run_bare_file_alias_does_not_claim_disabled_alias(self):
        config = dict(GTD.DEFAULT_CONFIG)
        config["files"] = {
            "research": {
                "name": "Research",
                "path": "~/org/research.org",
                "bare": False,
            }
        }
        item = dict(AGENDA_ITEM)
        item["title"] = "Research notes"

        with (
            mock.patch("chiyo_cli.builtin_tools.gtd.agenda_items", return_value=[item]),
            mock.patch("chiyo_cli.builtin_tools.gtd.require_command"),
        ):
            result = GTD.Tool().run(
                ["research"],
                config=config,
                execute_shell_actions=False,
            )

        self.assertEqual(
            result,
            ShellAction.command(["emacsclient", "-n", "+42:3", "/tmp/chiyo/tasks.org"]),
        )

    def test_run_open_unknown_file_alias_fails(self):
        with self.assertRaises(SystemExit):
            GTD.Tool().run(["open", "missing"], config=GTD.DEFAULT_CONFIG)

    def test_run_view_uses_configured_view_items(self):
        with (
            mock.patch("chiyo_cli.builtin_tools.gtd.agenda_view_items", return_value=[AGENDA_ITEM]) as items,
            mock.patch("chiyo_cli.builtin_tools.gtd.require_command"),
        ):
            result = GTD.Tool().run(
                ["view", "todo", "release"],
                config=GTD.DEFAULT_CONFIG,
                execute_shell_actions=False,
            )

        items.assert_called_once_with(GTD.DEFAULT_CONFIG, "todo")
        self.assertEqual(
            result,
            ShellAction.command(["emacsclient", "-n", "+42:3", "/tmp/chiyo/tasks.org"]),
        )

    def test_run_view_requires_name(self):
        with self.assertRaises(SystemExit):
            GTD.Tool().run(["view"], config=GTD.DEFAULT_CONFIG)

    def test_run_view_unknown_name_fails(self):
        with self.assertRaises(SystemExit):
            GTD.Tool().run(["view", "missing"], config=GTD.DEFAULT_CONFIG)

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
