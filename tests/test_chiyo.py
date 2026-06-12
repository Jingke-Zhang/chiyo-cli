import os
import tempfile
import unittest
from io import StringIO
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock

from chiyo_cli.toolkit import ShellAction


REPO_ROOT = Path(__file__).resolve().parents[1]
CHIYO = SourceFileLoader("chiyo", str(REPO_ROOT / "bin" / "chiyo")).load_module()
FIXTURE_TOOL_DIR = REPO_ROOT / "tests" / "fixtures" / "user_tools"


class ChiyoTests(unittest.TestCase):
    def test_init_zsh_prints_loader_for_installed_shell_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            completion_dir = os.path.join(temp_dir, "zsh")
            shell_dir = os.path.join(temp_dir, "shell")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        "tool_dirs = []",
                        "enabled_tools = []",
                        'wrapper_dir = "~/.local/bin"',
                        f'completion_dir = "{completion_dir}"',
                        f'shell_dir = "{shell_dir}"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                script = CHIYO.init_zsh()

        self.assertIn(
            "# Config: run `chiyo config init --all --append` once for explicit defaults.",
            script,
        )
        self.assertNotIn("export PATH=", script)
        self.assertIn(
            f'fpath=("{completion_dir}" $fpath)',
            script,
        )
        self.assertIn("autoload -Uz compinit", script)
        self.assertIn("compinit", script)
        self.assertIn(f'for chiyo_shell_file in "{shell_dir}"/*.zsh; do', script)
        self.assertIn('source "$chiyo_shell_file"', script)

    @mock.patch("chiyo.shutil.which")
    def test_doctor_lines_reports_missing_development_install(self, which):
        which.return_value = None

        with tempfile.TemporaryDirectory() as temp_dir:
            local_bin = os.path.join(temp_dir, ".local", "bin")
            site_functions = os.path.join(
                temp_dir,
                ".local",
                "share",
                "zsh",
                "site-functions",
            )
            config_path = os.path.join(temp_dir, "config.toml")

            with mock.patch.object(CHIYO, "LOCAL_BIN_DIR", local_bin):
                with mock.patch.object(CHIYO, "ZSH_SITE_FUNCTIONS_DIR", site_functions):
                    with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                        with mock.patch.dict(os.environ, {"HOME": temp_dir, "PATH": ""}):
                            lines = CHIYO.doctor_lines()

        self.assertIn("missing fzf: not found", lines)
        self.assertIn("missing rg: not found", lines)
        self.assertIn(f"missing chiyo symlink: {local_bin}/chiyo not found", lines)
        self.assertIn(f"todo    PATH: add {local_bin} to PATH", lines)
        self.assertIn("Run: ./install.sh", lines)
        self.assertIn("Review todo items above.", lines)

    @mock.patch("chiyo.shutil.which")
    def test_doctor_lines_reports_valid_development_install(self, which):
        which.side_effect = lambda name: f"/usr/bin/{name}"

        with tempfile.TemporaryDirectory() as temp_dir:
            local_bin = os.path.join(temp_dir, ".local", "bin")
            site_functions = os.path.join(
                temp_dir,
                ".local",
                "share",
                "zsh",
                "site-functions",
            )
            config_path = os.path.join(temp_dir, "config.toml")
            zshrc_path = os.path.join(temp_dir, ".zshrc")
            os.makedirs(local_bin)
            os.makedirs(site_functions)
            Path(config_path).write_text("", encoding="utf-8")
            Path(zshrc_path).write_text(CHIYO.SHELL_INTEGRATION, encoding="utf-8")

            for command in CHIYO.COMMANDS:
                os.symlink(
                    os.path.join(CHIYO.BIN_DIR, command),
                    os.path.join(local_bin, command),
                )

            with mock.patch.object(CHIYO, "LOCAL_BIN_DIR", local_bin):
                with mock.patch.object(CHIYO, "ZSH_SITE_FUNCTIONS_DIR", site_functions):
                    with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                        with mock.patch.dict(
                            os.environ,
                            {
                                "HOME": temp_dir,
                                "PATH": os.pathsep.join([local_bin, "/usr/bin"]),
                            },
                        ):
                            lines = CHIYO.doctor_lines()

        self.assertIn(f"ok      chiyo symlink: {local_bin}/chiyo -> {CHIYO.BIN_DIR}/chiyo", lines)
        self.assertIn(
            f"ok      zsh integration: {zshrc_path} contains {CHIYO.SHELL_INTEGRATION}",
            lines,
        )
        self.assertNotIn("Run: ./install.sh", lines)

    def test_check_symlink_warns_when_link_points_elsewhere(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = os.path.join(temp_dir, "bm")
            os.symlink("/old/repo/bin/bm", target)

            self.assertEqual(
                CHIYO.check_symlink("bm symlink", target, "/new/repo/bin/bm"),
                (
                    "warn",
                    f"{target} -> /old/repo/bin/bm; expected /new/repo/bin/bm",
                    "bm symlink",
                ),
            )

    def test_validate_config_init_requires_target(self):
        args = mock.Mock(all=False, tools=[])

        with self.assertRaises(ValueError):
            CHIYO.validate_config_init_args(args)

    def test_config_init_all_write_writes_every_tool_when_config_is_empty(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_path = os.path.join(temp_dir, "tools.toml")

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_path):
                    targets = CHIYO.validate_config_init_args(
                        mock.Mock(all=True, tools=[])
                    )
                    lines = CHIYO.config_init_lines(targets, "write")

            config_content = Path(config_path).read_text(encoding="utf-8")
            tools_content = Path(tools_path).read_text(encoding="utf-8")

        self.assertIn("wrote [chiyo] config", "\n".join(lines))
        self.assertIn("wrote [gop] config", "\n".join(lines))
        self.assertIn("wrote [ws] config", "\n".join(lines))
        self.assertIn("[chiyo]", config_content)
        self.assertIn('enabled_tools = ["gop", "ws"]', config_content)
        self.assertNotIn("[ws]", config_content)
        self.assertIn("[gop]", tools_content)
        self.assertIn("[ws.engines.g]", tools_content)
        self.assertNotIn("[bm]", tools_content)

    def test_config_init_all_uses_current_enabled_tools(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                '[chiyo]\nenabled_tools = ["bm", "zo"]\n',
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_path):
                    targets = CHIYO.validate_config_init_args(
                        mock.Mock(all=True, tools=[])
                    )
                    lines = CHIYO.config_init_lines(targets, "append")

            tools_content = Path(tools_path).read_text(encoding="utf-8")

        self.assertEqual(["chiyo", "bm", "zo"], targets)
        self.assertIn("append [chiyo] defaults", "\n".join(lines))
        self.assertIn("append [bm] config", "\n".join(lines))
        self.assertIn("append [zo] config", "\n".join(lines))
        self.assertIn("[bm]", tools_content)
        self.assertIn("[zo]", tools_content)
        self.assertNotIn("[gop]", tools_content)
        self.assertNotIn("[ws]", tools_content)

    def test_config_init_write_refuses_non_empty_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_path = os.path.join(temp_dir, "tools.toml")
            Path(tools_path).write_text("[other]\n", encoding="utf-8")

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_path):
                    with self.assertRaises(CHIYO.ConfigInitRefused):
                        CHIYO.config_init_lines(["ws"], "write")

    def test_config_init_append_skips_existing_and_adds_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_path = os.path.join(temp_dir, "tools.toml")
            Path(tools_path).write_text("[ws]\nfzf_prompt = \"old> \"\n", encoding="utf-8")

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_path):
                    lines = CHIYO.config_init_lines(["ws", "app"], "append")

            content = Path(tools_path).read_text(encoding="utf-8")

        self.assertIn("skip [ws] config: already exists", lines)
        self.assertIn("append [app] config", "\n".join(lines))
        self.assertIn("[app.alias]", content)
        self.assertIn('fzf_prompt = "old> "', content)

    def test_config_init_append_adds_missing_bm_defaults(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_path = os.path.join(temp_dir, "tools.toml")
            Path(tools_path).write_text(
                "\n".join(
                    [
                        "[bm]",
                        'skip_folders = ["Bookmarks"]',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_path):
                    lines = CHIYO.config_init_lines(["bm"], "append")

            content = Path(tools_path).read_text(encoding="utf-8")

        self.assertIn("append [bm] defaults", "\n".join(lines))
        self.assertIn('bookmarks_path = "~/Library/Safari/Bookmarks.plist"', content)
        self.assertIn('skip_folders = ["Bookmarks"]', content)
        self.assertIn('fzf_prompt = "bm> "', content)
        self.assertIn('browser = "Safari"', content)

    def test_config_init_append_preserves_existing_bm_defaults(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_path = os.path.join(temp_dir, "tools.toml")
            Path(tools_path).write_text(
                "\n".join(
                    [
                        "[bm]",
                        'bookmarks_path = "~/Bookmarks.plist"',
                        'skip_folders = ["Bookmarks"]',
                        'fzf_prompt = "bookmarks> "',
                        'browser = "Google Chrome"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_path):
                    lines = CHIYO.config_init_lines(["bm"], "append")

            content = Path(tools_path).read_text(encoding="utf-8")

        self.assertIn("skip [bm] config: already exists", lines)
        self.assertIn('bookmarks_path = "~/Bookmarks.plist"', content)
        self.assertIn('fzf_prompt = "bookmarks> "', content)
        self.assertIn('browser = "Google Chrome"', content)

    def test_config_init_force_replaces_selected_tool(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_path = os.path.join(temp_dir, "tools.toml")
            Path(tools_path).write_text(
                "\n".join(
                    [
                        "[other]",
                        'name = "kept"',
                        "",
                        "[ws]",
                        'fzf_prompt = "old> "',
                        "",
                        "[ws.engines.old]",
                        'name = "Old"',
                        'url = "https://old.test?q={query}"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_path):
                    CHIYO.config_init_lines(["ws"], "force")

            content = Path(tools_path).read_text(encoding="utf-8")

        self.assertIn("[other]", content)
        self.assertIn("[ws.engines.g]", content)
        self.assertNotIn("[ws.engines.old]", content)

    @mock.patch("chiyo.shutil.which")
    def test_doctor_lines_reports_available_command(self, which):
        which.side_effect = lambda name: f"/usr/bin/{name}"

        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.object(CHIYO, "LOCAL_BIN_DIR", os.path.join(temp_dir, "bin")):
                with mock.patch.object(
                    CHIYO,
                    "ZSH_SITE_FUNCTIONS_DIR",
                    os.path.join(temp_dir, "site-functions"),
                ):
                    with mock.patch.dict(os.environ, {"HOME": temp_dir}):
                        lines = CHIYO.doctor_lines()

        self.assertIn("ok      fzf: /usr/bin/fzf", lines)

    def test_tool_enable_and_disable_update_chiyo_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                self.assertEqual(CHIYO.enable_tool_lines("paper"), ["enabled tool: paper"])
                self.assertEqual(CHIYO.disable_tool_lines("paper"), ["disabled tool: paper"])
                self.assertEqual(
                    CHIYO.disable_tool_lines("paper"),
                    ["tool already disabled: paper"],
                )

            content = Path(config_path).read_text(encoding="utf-8")

        self.assertIn("[chiyo]", content)
        self.assertIn('enabled_tools = ["gop", "ws"]', content)

    def test_tool_list_shows_discovered_tools_and_enabled_status(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = ["paper"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                lines = CHIYO.tool_list_lines()

        output = "\n".join(lines)
        self.assertIn("enabled  paper", output)
        self.assertIn("Paper Search by Fixture Author", output)
        self.assertIn("disabled disabled-notes", output)
        self.assertIn("warn", output)
        self.assertIn("missing_author.py", output)
        self.assertNotIn("# Paper Search", output)

    def test_tool_list_can_include_docs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = []',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                lines = CHIYO.tool_list_lines(include_docs=True)

        self.assertIn("# Paper Search", "\n".join(lines))

    def test_tool_doc_lines_returns_docs_for_discoverable_tool(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = []',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                lines = CHIYO.tool_doc_lines("paper")

        self.assertIn("# Paper Search", "\n".join(lines))

    def test_tool_doc_lines_returns_none_for_unknown_tool(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = []',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                lines = CHIYO.tool_doc_lines("missing")

        self.assertIsNone(lines)

    def test_main_doc_prints_docs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = []',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch("sys.stdout", new_callable=StringIO) as stdout:
                    CHIYO.main(["doc", "paper"])

        self.assertIn("# Paper Search", stdout.getvalue())

    def test_run_tool_runs_enabled_tool_with_tools_toml_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "papers"
            root.mkdir()
            alpha = root / "alpha.pdf"
            beta = root / "beta.pdf"
            alpha.write_text("alpha", encoding="utf-8")
            beta.write_text("beta", encoding="utf-8")
            config_path = os.path.join(temp_dir, "config.toml")
            tools_config_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = ["paper"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )
            Path(tools_config_path).write_text(
                "\n".join(
                    [
                        "[paper]",
                        f'root = "{root}"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_config_path):
                    result = CHIYO.run_tool("paper", ["alpha"])

        self.assertEqual(result, str(alpha))

    def test_run_tool_rejects_disabled_tool(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = []',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with self.assertRaises(CHIYO.ToolCommandError):
                    CHIYO.run_tool("paper", [])

    def test_run_tool_rejects_unknown_enabled_tool(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = ["missing"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with self.assertRaises(CHIYO.ToolCommandError):
                    CHIYO.run_tool("missing", [])

    def test_shell_tool_lines_render_shell_action(self):
        with mock.patch.object(CHIYO, "run_tool") as run_tool:
            run_tool.return_value = ShellAction.cd("/tmp/My Project")

            lines = CHIYO.shell_tool_lines("proj", ["my"])

        self.assertEqual(lines, ["cd '/tmp/My Project'"])
        run_tool.assert_called_once_with(
            "proj",
            ["my"],
            execute_shell_actions=False,
        )

    def test_shell_tool_lines_prints_plain_result_safely(self):
        with mock.patch.object(CHIYO, "run_tool") as run_tool:
            run_tool.return_value = "plain value"

            lines = CHIYO.shell_tool_lines("tool", [])

        self.assertEqual(lines, ["printf '%s\\n' 'plain value'"])

    def test_run_tool_runs_builtin_ws(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_config_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        'tool_dirs = []',
                        'enabled_tools = ["ws"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_config_path):
                    with mock.patch("chiyo_cli.toolkit.open_location") as open_location:
                        result = CHIYO.run_tool("ws", ["g", "wavelet", "tree"])

        self.assertEqual(result, "https://www.google.com/search?q=wavelet%20tree")
        open_location.assert_called_once_with(
            "https://www.google.com/search?q=wavelet%20tree"
        )

    def test_run_tool_runs_builtin_app_alias(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_config_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        'tool_dirs = []',
                        'enabled_tools = ["app"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )
            Path(tools_config_path).write_text(
                "\n".join(
                    [
                        "[app.alias]",
                        'browser = "Safari"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_config_path):
                    with mock.patch("chiyo_cli.builtin_tools.app.open_app") as open_app:
                        result = CHIYO.run_tool("app", ["browser"])

        self.assertEqual(result, {"name": "Safari", "path": None})
        open_app.assert_called_once()
        self.assertEqual(open_app.call_args.args[0], {"name": "Safari", "path": None})

    def test_run_tool_runs_builtin_bm_print_url(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_config_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        'tool_dirs = []',
                        'enabled_tools = ["bm"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_config_path):
                    with mock.patch("chiyo_cli.builtin_tools.bm.load_bookmarks") as load_bookmarks:
                        load_bookmarks.return_value = [
                            ("Docs/Example", "https://example.test"),
                        ]
                        with mock.patch("sys.stdout", new_callable=StringIO) as stdout:
                            result = CHIYO.run_tool(
                                "bm",
                                ["--print-url", "Example"],
                            )

        self.assertEqual(result, "https://example.test")
        self.assertEqual(stdout.getvalue(), "https://example.test\n")

    def test_run_tool_runs_builtin_zo_default_open(self):
        item = {
            "key": "ITEMKEY1",
            "library_type": "user",
            "title": "Linear Algebra Done Right",
            "creators": "Sheldon Axler",
            "date": "2015",
            "item_type": "book",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_config_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        'tool_dirs = []',
                        'enabled_tools = ["zo"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_config_path):
                    with mock.patch("chiyo_cli.builtin_tools.zo.load_items") as load_items:
                        with mock.patch("chiyo_cli.builtin_tools.zo.open_location") as open_location:
                            load_items.return_value = [item]
                            result = CHIYO.run_tool("zo", ["linear"])

        self.assertEqual(result, "zotero://select/library/items/ITEMKEY1")
        open_location.assert_called_once()
        self.assertEqual(
            open_location.call_args.args[0],
            "zotero://select/library/items/ITEMKEY1",
        )

    def test_shell_tool_lines_runs_builtin_proj(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "My Project"
            project.mkdir()
            config_path = os.path.join(temp_dir, "config.toml")
            tools_config_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        'tool_dirs = []',
                        'enabled_tools = ["proj"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_config_path):
                    with mock.patch("chiyo_cli.builtin_tools.proj.all_projects") as all_projects:
                        with mock.patch("chiyo_cli.builtin_tools.proj.normalize_roots") as normalize_roots:
                            normalize_roots.return_value = [temp_dir]
                            all_projects.return_value = [str(project)]
                            lines = CHIYO.shell_tool_lines("proj", ["Project"])

        self.assertEqual(lines, [ShellAction.cd(str(project)).render_shell()])

    def test_shell_tool_lines_runs_builtin_gop_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "Target Dir"
            target.mkdir()
            config_path = os.path.join(temp_dir, "config.toml")
            tools_config_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        'tool_dirs = []',
                        'enabled_tools = ["gop"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )
            Path(tools_config_path).write_text(
                f'[gop]\nroots = ["{temp_dir}"]\nexclude = []\nfzf_prompt = "gop> "\n',
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_config_path):
                    with mock.patch("chiyo_cli.builtin_tools.gop.run_fd") as run_fd:
                        run_fd.return_value = [str(target)]
                        lines = CHIYO.shell_tool_lines("gop", ["Target"])

        self.assertEqual(lines, [ShellAction.cd(str(target)).render_shell()])

    def test_shell_tool_lines_expands_gop_config_roots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir)
            root = home / "Documents"
            root.mkdir()
            target = root / "Target Dir"
            target.mkdir()
            config_path = os.path.join(temp_dir, "config.toml")
            tools_config_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        'tool_dirs = []',
                        'enabled_tools = ["gop"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )
            Path(tools_config_path).write_text(
                '[gop]\nroots = ["~/Documents"]\nexclude = []\nfzf_prompt = "gop> "\n',
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_config_path):
                    with mock.patch.dict(os.environ, {"HOME": str(home)}):
                        with mock.patch("chiyo_cli.builtin_tools.gop.run_fd") as run_fd:
                            run_fd.return_value = [str(target)]
                            lines = CHIYO.shell_tool_lines("gop", ["Target"])

        self.assertEqual(lines, [ShellAction.cd(str(target)).render_shell()])
        self.assertEqual(run_fd.call_args.args[1], [str(root)])

    def test_shell_tool_lines_runs_builtin_gop_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "paper.pdf"
            target.write_text("pdf", encoding="utf-8")
            config_path = os.path.join(temp_dir, "config.toml")
            tools_config_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        'tool_dirs = []',
                        'enabled_tools = ["gop"]',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )
            Path(tools_config_path).write_text(
                f'[gop]\nroots = ["{temp_dir}"]\nexclude = []\nfzf_prompt = "gop> "\n',
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_config_path):
                    with mock.patch("chiyo_cli.builtin_tools.gop.run_fd") as run_fd:
                        run_fd.return_value = [str(target)]
                        lines = CHIYO.shell_tool_lines("gop", ["paper"])

        self.assertEqual(lines, [ShellAction.open(str(target)).render_shell()])

    def test_tool_doc_lines_returns_builtin_docs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        'tool_dirs = []',
                        'enabled_tools = []',
                        'wrapper_dir = "~/.local/bin"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                lines = CHIYO.tool_doc_lines("ws")

        self.assertIn("# ws", "\n".join(lines))

    def test_install_tool_writes_wrapper_for_enabled_tool(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper_dir = Path(temp_dir) / "bin"
            completion_dir = Path(temp_dir) / "zsh"
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = ["paper"]',
                        f'wrapper_dir = "{wrapper_dir}"',
                        f'completion_dir = "{completion_dir}"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                lines = CHIYO.install_tool_lines("paper")

            wrapper = wrapper_dir / "paper"
            self.assertIn(f"installed paper: {wrapper}", lines)
            self.assertEqual(wrapper.read_text(encoding="utf-8"), CHIYO.wrapper_script("paper"))
            self.assertTrue(os.access(wrapper, os.X_OK))
            completion = completion_dir / "_paper"
            self.assertIn(f"installed _paper: {completion}", lines)
            self.assertEqual(
                completion.read_text(encoding="utf-8"),
                CHIYO.completion_script("paper"),
            )

    def test_install_shell_tool_writes_function_completion_and_helper(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper_dir = Path(temp_dir) / "bin"
            completion_dir = Path(temp_dir) / "zsh"
            shell_dir = Path(temp_dir) / "shell"
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        "tool_dirs = []",
                        'enabled_tools = ["gop"]',
                        f'wrapper_dir = "{wrapper_dir}"',
                        f'completion_dir = "{completion_dir}"',
                        f'shell_dir = "{shell_dir}"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                lines = CHIYO.install_tool_lines("gop")

            shell_file = shell_dir / "gop.zsh"
            completion = completion_dir / "_gop"
            helper = wrapper_dir / "gop-select"
            wrapper = wrapper_dir / "gop"

            self.assertIn(f"installed gop shell: {shell_file}", lines)
            self.assertIn(f"installed _gop: {completion}", lines)
            self.assertIn(f"installed gop-select: {helper}", lines)
            self.assertEqual(
                shell_file.read_text(encoding="utf-8"),
                CHIYO.shell_function_script("gop"),
            )
            self.assertEqual(
                completion.read_text(encoding="utf-8"),
                CHIYO.completion_script("gop"),
            )
            self.assertTrue(helper.is_symlink())
            self.assertEqual(os.readlink(helper), os.path.join(CHIYO.BIN_DIR, "gop-select"))
            self.assertFalse(wrapper.exists())

    def test_install_tool_warns_when_tool_is_disabled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper_dir = Path(temp_dir) / "bin"
            completion_dir = Path(temp_dir) / "zsh"
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = []',
                        f'wrapper_dir = "{wrapper_dir}"',
                        f'completion_dir = "{completion_dir}"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                lines = CHIYO.install_tool_lines("paper")

        self.assertIn("warn    paper installed but disabled for chiyo run", lines)

    def test_install_tool_refuses_to_replace_existing_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper_dir = Path(temp_dir) / "bin"
            wrapper_dir.mkdir()
            (wrapper_dir / "paper").write_text("user file\n", encoding="utf-8")
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = ["paper"]',
                        f'wrapper_dir = "{wrapper_dir}"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with self.assertRaisesRegex(CHIYO.ToolCommandError, "refusing"):
                    CHIYO.install_tool_lines("paper")

    def test_install_tool_refuses_to_replace_existing_completion(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper_dir = Path(temp_dir) / "bin"
            completion_dir = Path(temp_dir) / "zsh"
            completion_dir.mkdir()
            (completion_dir / "_paper").write_text("user completion\n", encoding="utf-8")
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = ["paper"]',
                        f'wrapper_dir = "{wrapper_dir}"',
                        f'completion_dir = "{completion_dir}"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with self.assertRaisesRegex(CHIYO.ToolCommandError, "refusing"):
                    CHIYO.install_tool_lines("paper")

    def test_uninstall_tool_removes_generated_wrapper(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper_dir = Path(temp_dir) / "bin"
            wrapper_dir.mkdir()
            wrapper = wrapper_dir / "paper"
            wrapper.write_text(CHIYO.wrapper_script("paper"), encoding="utf-8")
            completion_dir = Path(temp_dir) / "zsh"
            completion_dir.mkdir()
            completion = completion_dir / "_paper"
            completion.write_text(CHIYO.completion_script("paper"), encoding="utf-8")
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = ["paper"]',
                        f'wrapper_dir = "{wrapper_dir}"',
                        f'completion_dir = "{completion_dir}"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                lines = CHIYO.uninstall_tool_lines("paper")

        self.assertEqual(
            lines,
            [
                f"uninstalled paper: {wrapper}",
                f"uninstalled _paper: {completion}",
            ],
        )
        self.assertFalse(wrapper.exists())
        self.assertFalse(completion.exists())

    def test_uninstall_shell_tool_removes_generated_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper_dir = Path(temp_dir) / "bin"
            wrapper_dir.mkdir()
            completion_dir = Path(temp_dir) / "zsh"
            completion_dir.mkdir()
            shell_dir = Path(temp_dir) / "shell"
            shell_dir.mkdir()
            shell_file = shell_dir / "gop.zsh"
            shell_file.write_text(CHIYO.shell_function_script("gop"), encoding="utf-8")
            completion = completion_dir / "_gop"
            completion.write_text(CHIYO.completion_script("gop"), encoding="utf-8")
            helper = wrapper_dir / "gop-select"
            helper.symlink_to(os.path.join(CHIYO.BIN_DIR, "gop-select"))
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        "tool_dirs = []",
                        'enabled_tools = ["gop"]',
                        f'wrapper_dir = "{wrapper_dir}"',
                        f'completion_dir = "{completion_dir}"',
                        f'shell_dir = "{shell_dir}"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                lines = CHIYO.uninstall_tool_lines("gop")

            self.assertEqual(
                lines,
                [
                    f"uninstalled gop shell: {shell_file}",
                    f"uninstalled _gop: {completion}",
                    f"uninstalled gop-select: {helper}",
                ],
            )
            self.assertFalse(shell_file.exists())
            self.assertFalse(completion.exists())
            self.assertFalse(helper.exists())

    def test_uninstall_tool_refuses_non_generated_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper_dir = Path(temp_dir) / "bin"
            wrapper_dir.mkdir()
            (wrapper_dir / "paper").write_text("user file\n", encoding="utf-8")
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = ["paper"]',
                        f'wrapper_dir = "{wrapper_dir}"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with self.assertRaisesRegex(CHIYO.ToolCommandError, "refusing"):
                    CHIYO.uninstall_tool_lines("paper")

    def test_user_tool_doctor_checks_report_metadata_and_install_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper_dir = Path(temp_dir) / "bin"
            wrapper_dir.mkdir()
            completion_dir = Path(temp_dir) / "zsh"
            completion_dir.mkdir()
            (wrapper_dir / "paper").write_text(
                CHIYO.wrapper_script("paper"),
                encoding="utf-8",
            )
            (completion_dir / "_paper").write_text(
                CHIYO.completion_script("paper"),
                encoding="utf-8",
            )
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = ["missing"]',
                        f'wrapper_dir = "{wrapper_dir}"',
                        f'completion_dir = "{completion_dir}"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                lines = [
                    f"{status:7} {label}: {detail}"
                    for status, detail, label in CHIYO.user_tool_doctor_checks()
                ]

        output = "\n".join(lines)
        self.assertIn("ok      user tool paper metadata:", output)
        self.assertIn("warn    user tool missing: enabled but not discoverable", output)
        self.assertIn("ok      user tool paper wrapper:", output)
        self.assertIn("ok      user tool paper zsh:", output)
        self.assertIn(
            "warn    user tool paper: paper installed but disabled for chiyo run",
            output,
        )
        self.assertIn("warn    user tool missing_author.py:", output)
        self.assertIn("warn    user tool conflicting_flags.py:", output)

    def test_user_tool_doctor_checks_warn_when_installed_completion_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper_dir = Path(temp_dir) / "bin"
            wrapper_dir.mkdir()
            completion_dir = Path(temp_dir) / "zsh"
            (wrapper_dir / "paper").write_text(
                CHIYO.wrapper_script("paper"),
                encoding="utf-8",
            )
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = ["paper"]',
                        f'wrapper_dir = "{wrapper_dir}"',
                        f'completion_dir = "{completion_dir}"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                lines = [
                    f"{status:7} {label}: {detail}"
                    for status, detail, label in CHIYO.user_tool_doctor_checks()
                ]

        self.assertIn(
            f"warn    user tool paper zsh: {completion_dir / '_paper'} not found",
            "\n".join(lines),
        )


if __name__ == "__main__":
    unittest.main()
