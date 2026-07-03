import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from chiyo_cli.builtin_tools import workspace as WS


class WorkspaceTests(unittest.TestCase):
    def test_session_name_sanitizes_workspace_names(self):
        self.assertEqual(WS.session_name("My Project"), "My-Project")
        self.assertEqual(WS.session_name("api/server", "dev-"), "dev-server")

    def test_tmux_sessions_parses_session_output(self):
        result = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="cli\t/Users/me/cli\nnotes\t/Users/me/notes\n",
            stderr="",
        )

        with mock.patch.object(WS, "run_tmux", return_value=result):
            sessions = WS.tmux_sessions(lambda message: self.fail(message))

        self.assertEqual(
            sessions,
            [
                {
                    "kind": "session",
                    "name": "cli",
                    "session": "cli",
                    "path": "/Users/me/cli",
                    "exists": True,
                },
                {
                    "kind": "session",
                    "name": "notes",
                    "session": "notes",
                    "path": "/Users/me/notes",
                    "exists": True,
                },
            ],
        )

    def test_tmux_sessions_returns_empty_when_server_is_missing(self):
        result = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr="no server running",
        )

        with mock.patch.object(WS, "run_tmux", return_value=result):
            self.assertEqual(WS.tmux_sessions(lambda message: self.fail(message)), [])

    def test_items_merge_sessions_aliases_and_projects(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "cli-tools"
            project.mkdir()
            config = {
                **WS.DEFAULT_CONFIG,
                "roots": [temp_dir],
                "alias": {"notes": "~/notes"},
            }
            sessions = [
                {
                    "kind": "session",
                    "name": "cli-tools",
                    "session": "cli-tools",
                    "path": str(project),
                    "exists": True,
                }
            ]

            with mock.patch.object(WS.Tool, "sessions", return_value=sessions):
                with mock.patch.object(WS.project, "all_projects", return_value=[str(project)]):
                    items = WS.Tool().items(config)

        self.assertEqual([item["session"] for item in items], ["cli-tools", "notes"])
        self.assertEqual(items[1]["kind"], "alias")

    def test_run_new_creates_and_attaches_session(self):
        calls = []

        def fake_run_tmux(args, fail, allow_failure=False):
            calls.append(args)
            return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.dict("os.environ", {"TMUX": ""}, clear=False):
                with mock.patch.object(WS, "run_tmux", side_effect=fake_run_tmux):
                    result = WS.Tool().run(["--new", "My Project", temp_dir])

        self.assertEqual(result, "My-Project")
        self.assertEqual(calls[0], ["new-session", "-d", "-s", "My-Project", "-c", temp_dir])
        self.assertEqual(calls[1], ["attach-session", "-t", "My-Project"])

    def test_run_switches_inside_tmux(self):
        calls = []

        def fake_run_tmux(args, fail, allow_failure=False):
            calls.append(args)
            return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        with mock.patch.dict("os.environ", {"TMUX": "/tmp/tmux"}):
            with mock.patch.object(WS, "run_tmux", side_effect=fake_run_tmux):
                result = WS.Tool().run(["--new", "cli", "/tmp"])

        self.assertEqual(result, "cli")
        self.assertEqual(calls[-1], ["switch-client", "-t", "cli"])

    def test_run_kill_selects_matching_session(self):
        sessions = [
            {
                "kind": "session",
                "name": "cli",
                "session": "cli",
                "path": "/tmp/cli",
                "exists": True,
            }
        ]

        with mock.patch.object(WS.Tool, "sessions", return_value=sessions):
            with mock.patch.object(WS, "kill_session", return_value="cli") as kill:
                result = WS.Tool().run(["--kill", "cli"])

        self.assertEqual(result, "cli")
        kill.assert_called_once()
        self.assertEqual(kill.call_args.args[0], "cli")

    def test_run_rename_session(self):
        with mock.patch.object(WS, "rename_session", return_value="new-name") as rename:
            result = WS.Tool().run(["--rename", "old", "New Name"])

        self.assertEqual(result, "new-name")
        rename.assert_called_once()
        self.assertEqual(rename.call_args.args[:2], ("old", "New-Name"))


if __name__ == "__main__":
    unittest.main()
