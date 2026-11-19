import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from release import clean_build_artifacts, main, update_versions


class ReleaseScriptTests(unittest.TestCase):
    def test_update_versions_changes_both_package_metadata_files(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "sample"\nversion = "1.2.3"\n\n'
                '[tool.example]\nversion = "8.0"\n',
                encoding="utf-8",
            )
            (root / "setup.py").write_text(
                'setup(\n    name="sample",\n    version="1.2.3",\n)\n',
                encoding="utf-8",
            )

            update_versions(root, "2.0.0rc1")

            self.assertIn('version = "2.0.0rc1"', (root / "pyproject.toml").read_text())
            self.assertIn('version = "8.0"', (root / "pyproject.toml").read_text())
            self.assertIn('version="2.0.0rc1"', (root / "setup.py").read_text())

    def test_update_versions_rejects_missing_setting_without_partial_write(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            pyproject = root / "pyproject.toml"
            setup = root / "setup.py"
            pyproject.write_text('[project]\nversion = "1.0"\n', encoding="utf-8")
            setup.write_text('setup(name="sample")\n', encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "setup.py"):
                update_versions(root, "2.0")

            self.assertEqual(pyproject.read_text(encoding="utf-8"), '[project]\nversion = "1.0"\n')

    def test_clean_build_artifacts_removes_only_standard_outputs(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "dist").mkdir()
            (root / "build").mkdir()
            (root / "sample.egg-info").mkdir()
            (root / "keep.txt").write_text("keep", encoding="utf-8")

            clean_build_artifacts(root)

            self.assertFalse((root / "dist").exists())
            self.assertFalse((root / "build").exists())
            self.assertFalse((root / "sample.egg-info").exists())
            self.assertTrue((root / "keep.txt").exists())

    @patch("release.subprocess.run")
    @patch("release.clean_build_artifacts")
    @patch("release.update_versions")
    def test_upload_flag_runs_build_before_upload(
        self, update_versions_mock, clean_mock, run_mock
    ):
        with patch("release.Path.resolve", return_value=Path("/project/release.py")):
            with patch("pathlib.Path.glob", return_value=[Path("/project/dist/pkg.whl")]):
                main(["2.0.0", "--upload"])

        update_versions_mock.assert_called_once_with(Path("/project"), "2.0.0")
        clean_mock.assert_called_once_with(Path("/project"))
        self.assertEqual(run_mock.call_count, 2)
        self.assertEqual(run_mock.call_args_list[0].args[0][1:3], ["-m", "build"])
        self.assertEqual(
            run_mock.call_args_list[1].args[0][2:4],
            ["twine", "upload"],
        )
        self.assertEqual(run_mock.call_args_list[1].args[0][-1], "/project/dist/pkg.whl")


if __name__ == "__main__":
    unittest.main()
