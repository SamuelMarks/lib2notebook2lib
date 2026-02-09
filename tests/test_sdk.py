"""
Integration tests for the SDK layer.

simulates the full pipeline using temporary directories to ensure
modules (Parser, Scaffold, Writer) work together correctly.
"""

import unittest
import json
import tempfile
from pathlib import Path
from pydantic import ValidationError

from lib2notebook2lib.schema import UserConfig
from lib2notebook2lib.sdk import JupyterToPackage


class TestJupyterToPackage(unittest.TestCase):
    """Test suite for the main JupyterToPackage service."""

    def setUp(self) -> None:
        """
        Set up a temporary environment.

        Creates:
        1. A temporary directory.
        2. A dummy Jupyter Notebook file inside it.
        """
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        self.nb_path = self.root / "analysis.ipynb"

        nb_content = {
            "cells": [
                {
                    "cell_type": "code",
                    "execution_count": 1,
                    "source": ["import pandas as pd\n", "print('hello')"],
                },
                {
                    "cell_type": "code",
                    "execution_count": 2,
                    "source": "!pip install requests",
                },
            ],
            "metadata": {},
            "nbformat": 4,
            "nbformat_minor": 5,
        }

        with open(self.nb_path, "w", encoding="utf-8") as f:
            json.dump(nb_content, f)

    def tearDown(self) -> None:
        """Cleanup temporary resources."""
        self.temp_dir.cleanup()

    def test_end_to_end_conversion(self) -> None:
        """
        Test the full conversion flow from Notebook to Library.

        Verifies:
        - Directory creation.
        - Dependency detection (pandas, requests).
        - Code serialization (sanitization).
        - File existence (pyproject.toml).
        """
        config = UserConfig(
            notebook_path=self.nb_path,
            project_name="my-sdk-lib",
            output_dir=self.root,
            author_name="SDK Tester",
        )

        service = JupyterToPackage(config)
        result_path = service.convert()

        # Verify Return Path
        expected_path = self.root / "my-sdk-lib"
        self.assertEqual(result_path, expected_path)
        self.assertTrue(result_path.exists())

        # Verify Dependency Detection in requirements.txt
        req_path = result_path / "requirements.txt"
        self.assertTrue(req_path.exists())
        req_content = req_path.read_text(encoding="utf-8")
        self.assertIn("pandas", req_content)
        self.assertIn("requests", req_content)

        # Verify Code Sanitization in src/
        # Package name 'my-sdk-lib' becomes 'my_sdk_lib'
        init_path = result_path / "src" / "my_sdk_lib" / "__init__.py"
        self.assertTrue(init_path.exists())
        code_content = init_path.read_text(encoding="utf-8")
        self.assertIn("import pandas as pd", code_content)
        # Should NOT contain !pip command (sanitized)
        self.assertNotIn("!pip", code_content)

    def test_dependency_override(self) -> None:
        """
        Test that providing manual dependencies overrides auto-detection.
        """
        config = UserConfig(
            notebook_path=self.nb_path,
            project_name="manual-lib",
            output_dir=self.root,
            override_dependencies={"numpy", "scipy"},
        )

        service = JupyterToPackage(config)
        result_path = service.convert()

        req_path = result_path / "requirements.txt"
        req_content = req_path.read_text(encoding="utf-8")

        # Should have manual ones
        self.assertIn("numpy", req_content)
        self.assertIn("scipy", req_content)
        # Should NOT have auto-detected ones if override is strictly replacing
        self.assertNotIn("requests", req_content)

    def test_invalid_config_validation(self) -> None:
        """
        Test that Pydantic enforces schema constraints (e.g., file existence).
        """
        # Path does not exist
        with self.assertRaises(ValidationError):
            UserConfig(
                notebook_path=self.root / "ghost.ipynb", project_name="ghost-lib"
            )

    def test_bad_project_name(self) -> None:
        """
        Test that invalid project names raise ValidationError.
        """
        with self.assertRaises(ValidationError):
            UserConfig(
                notebook_path=self.nb_path, project_name="invalid name with spaces"
            )

    def test_writer_instantiation_logic(self) -> None:
        """
        Sanity check that writer uses the correct package slug.
        """
        config = UserConfig(
            notebook_path=self.nb_path,
            project_name="slug-check-lib",
            output_dir=self.root,
        )
        service = JupyterToPackage(config)
        service.convert()

        # Check underscore folder exists
        slug_dir = self.root / "slug-check-lib" / "src" / "slug_check_lib"
        self.assertTrue(slug_dir.exists())


if __name__ == "__main__":
    unittest.main()
