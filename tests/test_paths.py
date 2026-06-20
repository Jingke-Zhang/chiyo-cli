import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from chiyo_cli.paths import (
    absolute_path,
    compact_path,
    existing_dirs,
    expand_path,
    expand_paths,
)


class PathHelperTests(unittest.TestCase):
    def test_expand_path_expands_home_without_forcing_absolute(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.dict(os.environ, {"HOME": temp_dir}):
                self.assertEqual(expand_path("~/Docs"), os.path.join(temp_dir, "Docs"))
                self.assertEqual(expand_paths(["~/Docs"]), [os.path.join(temp_dir, "Docs")])

    def test_expand_path_accepts_shell_escaped_spaces(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.dict(os.environ, {"HOME": temp_dir}):
                self.assertEqual(
                    expand_path("~/OneDrive\\ -\\ The\\ University\\ of\\ Tokyo"),
                    os.path.join(temp_dir, "OneDrive - The University of Tokyo"),
                )

    def test_absolute_path_expands_home_and_normalizes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.dict(os.environ, {"HOME": temp_dir}):
                self.assertEqual(
                    absolute_path("~/Docs/.."),
                    temp_dir,
                )

    def test_compact_path_replaces_home_prefix(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.dict(os.environ, {"HOME": temp_dir}):
                self.assertEqual(compact_path(os.path.join(temp_dir, "Docs")), "~/Docs")

    def test_existing_dirs_expands_and_skips_missing_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            existing = Path(temp_dir) / "existing"
            existing.mkdir()
            missing = Path(temp_dir) / "missing"
            warnings = []

            result = existing_dirs(
                [existing, missing],
                "test root",
                warnings.append,
                self.fail,
            )

        self.assertEqual(result, [str(existing)])
        self.assertEqual(warnings, [f"skipping missing test root: {missing}"])

    def test_existing_dirs_can_fail_without_framework_callback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing"

            with self.assertRaisesRegex(RuntimeError, "no valid test roots found"):
                existing_dirs([missing], "test root")


if __name__ == "__main__":
    unittest.main()
