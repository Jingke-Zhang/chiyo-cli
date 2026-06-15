import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from chiyo_cli.commands import install as CHIYO


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_TOOL_DIR = REPO_ROOT / "tests" / "fixtures" / "user_tools"


class InstallTests(unittest.TestCase):
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
                        'enabled_tools = ["fixture/paper-search"]',
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

    def test_install_shell_tool_writes_function_and_completion(self):
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
                        'enabled_tools = ["jingke-zhang/go-or-pick"]',
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
            wrapper = wrapper_dir / "gop"

            self.assertIn(f"installed gop shell: {shell_file}", lines)
            self.assertIn(f"installed _gop: {completion}", lines)
            self.assertEqual(
                shell_file.read_text(encoding="utf-8"),
                CHIYO.shell_function_script("gop"),
            )
            self.assertEqual(
                completion.read_text(encoding="utf-8"),
                CHIYO.completion_script("gop"),
            )
            self.assertFalse((wrapper_dir / "gop-select").exists())
            self.assertFalse(wrapper.exists())

    def test_install_gtd_writes_shell_function_and_completion(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper_dir = Path(temp_dir) / "bin"
            wrapper_dir.mkdir()
            completion_dir = Path(temp_dir) / "zsh"
            shell_dir = Path(temp_dir) / "shell"
            old_wrapper = wrapper_dir / "gtd"
            old_wrapper.write_text(CHIYO.wrapper_script("gtd"), encoding="utf-8")
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        "tool_dirs = []",
                        'enabled_tools = ["jingke-zhang/gtd"]',
                        f'wrapper_dir = "{wrapper_dir}"',
                        f'completion_dir = "{completion_dir}"',
                        f'shell_dir = "{shell_dir}"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                lines = CHIYO.install_tool_lines("gtd")

            shell_file = shell_dir / "gtd.zsh"
            completion = completion_dir / "_gtd"
            wrapper = wrapper_dir / "gtd"

            self.assertIn(f"installed gtd shell: {shell_file}", lines)
            self.assertIn(f"installed _gtd: {completion}", lines)
            self.assertIn(f"removed old gtd wrapper: {old_wrapper}", lines)
            self.assertEqual(
                shell_file.read_text(encoding="utf-8"),
                CHIYO.shell_function_script("gtd"),
            )
            self.assertEqual(
                completion.read_text(encoding="utf-8"),
                CHIYO.completion_script("gtd"),
            )
            self.assertFalse(wrapper.exists())

    def test_install_shell_tool_alias_writes_function_and_completion(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper_dir = Path(temp_dir) / "bin"
            completion_dir = Path(temp_dir) / "zsh"
            shell_dir = Path(temp_dir) / "shell"
            config_path = os.path.join(temp_dir, "config.toml")
            tools_config_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        "tool_dirs = []",
                        'enabled_tools = ["jingke-zhang/go-or-pick"]',
                        f'wrapper_dir = "{wrapper_dir}"',
                        f'completion_dir = "{completion_dir}"',
                        f'shell_dir = "{shell_dir}"',
                    ]
                ),
                encoding="utf-8",
            )
            Path(tools_config_path).write_text(
                "\n".join(
                    [
                        '["jingke-zhang/go-or-pick"]',
                        'cmds = ["go"]',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_config_path):
                    lines = CHIYO.install_tool_lines("go")

            shell_file = shell_dir / "go.zsh"
            completion = completion_dir / "_go"
            wrapper = wrapper_dir / "go"

            self.assertIn(f"installed go shell: {shell_file}", lines)
            self.assertIn(f"installed _go: {completion}", lines)
            self.assertEqual(
                shell_file.read_text(encoding="utf-8"),
                CHIYO.shell_function_script("go"),
            )
            self.assertEqual(
                completion.read_text(encoding="utf-8"),
                CHIYO.completion_script("go"),
            )
            self.assertFalse(wrapper.exists())

    def test_install_tools_lines_installs_multiple_tools(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper_dir = Path(temp_dir) / "bin"
            completion_dir = Path(temp_dir) / "zsh"
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        "tool_dirs = []",
                        "enabled_tools = ["
                        '"jingke-zhang/application", '
                        '"jingke-zhang/zotero", '
                        '"jingke-zhang/web-search", '
                        '"jingke-zhang/workspace"'
                        "]",
                        f'wrapper_dir = "{wrapper_dir}"',
                        f'completion_dir = "{completion_dir}"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                lines = CHIYO.install_tools_lines(["app", "zo", "s", "ws"])

            for command in ["app", "zo", "s", "ws"]:
                wrapper = wrapper_dir / command
                completion = completion_dir / f"_{command}"
                self.assertIn(f"installed {command}: {wrapper}", lines)
                self.assertIn(f"installed _{command}: {completion}", lines)
                self.assertEqual(
                    wrapper.read_text(encoding="utf-8"),
                    CHIYO.wrapper_script(command),
                )
                self.assertEqual(
                    completion.read_text(encoding="utf-8"),
                    CHIYO.completion_script(command),
                )

    def test_install_tools_lines_rejects_duplicate_install_targets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        "tool_dirs = []",
                        'enabled_tools = ["jingke-zhang/application"]',
                        f'wrapper_dir = "{temp_dir}/bin"',
                        f'completion_dir = "{temp_dir}/zsh"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with self.assertRaisesRegex(CHIYO.ToolCommandError, "duplicate install target: app"):
                    CHIYO.install_tools_lines(["app", "jingke-zhang/application"])

    def test_install_tool_rejects_invalid_configured_cmd(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.toml")
            tools_config_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        f'tool_dirs = ["{FIXTURE_TOOL_DIR}"]',
                        'enabled_tools = []',
                        f'wrapper_dir = "{temp_dir}/bin"',
                        f'completion_dir = "{temp_dir}/zsh"',
                    ]
                ),
                encoding="utf-8",
            )
            Path(tools_config_path).write_text(
                "\n".join(
                    [
                        '["fixture/paper-search"]',
                        'cmds = ["paper", "Bad Cmd"]',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_config_path):
                    with self.assertRaisesRegex(CHIYO.ToolCommandError, "invalid cmd"):
                        CHIYO.install_tool_lines("paper")

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

        self.assertIn("warn    fixture/paper-search installed but disabled for chiyo run", lines)

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
                        'enabled_tools = ["fixture/paper-search"]',
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
                        'enabled_tools = ["fixture/paper-search"]',
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
                        'enabled_tools = ["fixture/paper-search"]',
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

    def test_uninstall_tools_lines_removes_multiple_generated_wrappers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper_dir = Path(temp_dir) / "bin"
            wrapper_dir.mkdir()
            completion_dir = Path(temp_dir) / "zsh"
            completion_dir.mkdir()
            config_path = os.path.join(temp_dir, "config.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        "tool_dirs = []",
                        'enabled_tools = ["jingke-zhang/application", "jingke-zhang/zotero"]',
                        f'wrapper_dir = "{wrapper_dir}"',
                        f'completion_dir = "{completion_dir}"',
                    ]
                ),
                encoding="utf-8",
            )

            for command in ["app", "zo"]:
                (wrapper_dir / command).write_text(
                    CHIYO.wrapper_script(command),
                    encoding="utf-8",
                )
                (completion_dir / f"_{command}").write_text(
                    CHIYO.completion_script(command),
                    encoding="utf-8",
                )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                lines = CHIYO.uninstall_tools_lines(["app", "zo"])

        self.assertIn(f"uninstalled app: {wrapper_dir / 'app'}", lines)
        self.assertIn(f"uninstalled _app: {completion_dir / '_app'}", lines)
        self.assertIn(f"uninstalled zo: {wrapper_dir / 'zo'}", lines)
        self.assertIn(f"uninstalled _zo: {completion_dir / '_zo'}", lines)
        self.assertFalse((wrapper_dir / "app").exists())
        self.assertFalse((completion_dir / "_app").exists())
        self.assertFalse((wrapper_dir / "zo").exists())
        self.assertFalse((completion_dir / "_zo").exists())

    def test_uninstall_tools_lines_rejects_duplicate_targets(self):
        with self.assertRaisesRegex(CHIYO.ToolCommandError, "duplicate uninstall target: app"):
            CHIYO.uninstall_tools_lines(["app", "jingke-zhang/application"])

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
                        'enabled_tools = ["jingke-zhang/go-or-pick"]',
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

    def test_uninstall_shell_tool_alias_removes_generated_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper_dir = Path(temp_dir) / "bin"
            wrapper_dir.mkdir()
            completion_dir = Path(temp_dir) / "zsh"
            completion_dir.mkdir()
            shell_dir = Path(temp_dir) / "shell"
            shell_dir.mkdir()
            shell_file = shell_dir / "go.zsh"
            shell_file.write_text(CHIYO.shell_function_script("go"), encoding="utf-8")
            completion = completion_dir / "_go"
            completion.write_text(CHIYO.completion_script("go"), encoding="utf-8")
            config_path = os.path.join(temp_dir, "config.toml")
            tools_config_path = os.path.join(temp_dir, "tools.toml")
            Path(config_path).write_text(
                "\n".join(
                    [
                        "[chiyo]",
                        "tool_dirs = []",
                        'enabled_tools = ["jingke-zhang/go-or-pick"]',
                        f'wrapper_dir = "{wrapper_dir}"',
                        f'completion_dir = "{completion_dir}"',
                        f'shell_dir = "{shell_dir}"',
                    ]
                ),
                encoding="utf-8",
            )
            Path(tools_config_path).write_text(
                "\n".join(
                    [
                        '["jingke-zhang/go-or-pick"]',
                        'cmds = ["go"]',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with mock.patch.object(CHIYO, "TOOLS_CONFIG_PATH", tools_config_path):
                    lines = CHIYO.uninstall_tool_lines("go")

            self.assertEqual(
                lines,
                [
                    f"uninstalled go shell: {shell_file}",
                    f"uninstalled _go: {completion}",
                ],
            )
            self.assertFalse(shell_file.exists())
            self.assertFalse(completion.exists())

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
                        'enabled_tools = ["fixture/paper-search"]',
                        f'wrapper_dir = "{wrapper_dir}"',
                        'completion_dir = "~/.local/share/zsh/site-functions"',
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.object(CHIYO, "CONFIG_PATH", config_path):
                with self.assertRaisesRegex(CHIYO.ToolCommandError, "refusing"):
                    CHIYO.uninstall_tool_lines("paper")



if __name__ == "__main__":
    unittest.main()
