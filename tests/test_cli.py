"""
End-to-End tests for the CLI module.
"""

import unittest
import json
import logging
import tempfile
from pathlib import Path
from io import StringIO
from unittest.mock import patch

from lib2notebook2lib.cli import main


class TestCLI(unittest.TestCase):
    """Test suite for the Command Line Interface."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        self.nb_path = self.root / "cli_test.ipynb"
        content = {
            "cells": [
                {
                    "cell_type": "code",
                    "execution_count": 1,
                    "source": ["import numpy as np\n", "print(np.pi)"],
                }
            ],
            "metadata": {},
            "nbformat": 4,
            "nbformat_minor": 5,
        }
        with open(self.nb_path, "w", encoding="utf-8") as f:
            json.dump(content, f)

        self.log_capture = StringIO()
        self.handler = logging.StreamHandler(self.log_capture)
        self.logger = logging.getLogger("lib2notebook2lib")
        self.logger.addHandler(self.handler)
        self.logger.propagate = False

    def tearDown(self) -> None:
        self.logger.removeHandler(self.handler)
        self.temp_dir.cleanup()

    def test_help_argument(self) -> None:
        with patch("sys.stdout", new=StringIO()):
            with self.assertRaises(SystemExit) as cm:
                main(["--help"])
            self.assertEqual(cm.exception.code, 0)

    def test_notebook_not_found(self) -> None:
        args = ["non_existent.ipynb", "--name", "mypkg"]
        with patch("lib2notebook2lib.cli.logger.error") as mock_log:
            exit_code = main(args)
            self.assertEqual(exit_code, 1)
            mock_log.assert_called_with(
                "Error: Notebook file not found: non_existent.ipynb"
            )

    def test_validation_error_bad_name(self) -> None:
        args = [str(self.nb_path), "--name", "invalid name with space"]
        with patch("lib2notebook2lib.cli.logger.error") as mock_log:
            exit_code = main(args)
            self.assertEqual(exit_code, 1)
            self.assertTrue(mock_log.called)

    def test_dry_run(self) -> None:
        args = [
            str(self.nb_path),
            "--name",
            "dry-run-pkg",
            "--output-dir",
            str(self.root),
            "--dry-run",
        ]
        exit_code = main(args)
        self.assertEqual(exit_code, 0)
        logs = self.log_capture.getvalue()
        self.assertIn("--- Dry Run Summary ---", logs)
        self.assertIn("numpy", logs)
        pkg_path = self.root / "dry-run-pkg"
        self.assertFalse(pkg_path.exists())

    def test_successful_conversion(self) -> None:
        args = [
            str(self.nb_path),
            "--name",
            "real-pkg",
            "--output-dir",
            str(self.root),
            "--author",
            "CLI Tester",
        ]
        exit_code = main(args)
        self.assertEqual(exit_code, 0)
        self.assertIn("Successfully created project", self.log_capture.getvalue())

    def test_overwrite_protection_without_force(self) -> None:
        pkg_path = self.root / "conflict-pkg"
        pkg_path.mkdir()
        args = [
            str(self.nb_path),
            "--name",
            "conflict-pkg",
            "--output-dir",
            str(self.root),
        ]
        with patch("lib2notebook2lib.cli.logger.error") as mock_log:
            exit_code = main(args)
            self.assertEqual(exit_code, 1)
            call_args = [c[0][0] for c in mock_log.call_args_list]
            self.assertTrue(any("exists" in s for s in call_args))

    def test_overwrite_with_force(self) -> None:
        pkg_path = self.root / "forced-pkg"
        pkg_path.mkdir()
        args = [
            str(self.nb_path),
            "--name",
            "forced-pkg",
            "--output-dir",
            str(self.root),
            "--force",
        ]
        exit_code = main(args)
        self.assertEqual(exit_code, 0)

    def test_main_with_exception(self) -> None:
        # Patched 'lib2notebook2lib.sdk.NotebookReader' because sdk.py
        # imports NotebookReader from parser. If we patch parser.NotebookReader,
        # sdk.py will still hold the reference to the original class.
        with patch(
            "lib2notebook2lib.sdk.NotebookReader", side_effect=Exception("Boom")
        ):
            args = [
                str(self.nb_path),
                "--name",
                "crash-pkg",
                "--output-dir",
                str(self.root),
            ]
            exit_code = main(args)
            self.assertEqual(exit_code, 1)
            self.assertIn("Unexpected error", self.log_capture.getvalue())


if __name__ == "__main__":
    unittest.main()
