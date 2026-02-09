"""
Unit tests for the notebook parsing logic in parser.py.

Covers JSON reading and orchestration of dependency analysis.
"""

import unittest
import json
import tempfile
import os
from pathlib import Path
from lib2notebook2lib.parser import NotebookReader, DependencyAnalyzer


class TestNotebookReader(unittest.TestCase):
    """Test suite for the NotebookReader class."""

    def setUp(self) -> None:
        """Create a temporary notebook file for testing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.nb_path = Path(self.temp_dir.name) / "test_nb.ipynb"

        self.nb_content = {
            "cells": [
                {"cell_type": "markdown", "source": ["# Title\n", "Description"]},
                {
                    "cell_type": "code",
                    "execution_count": 1,
                    "source": ["import os\n", "import sys"],
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
            json.dump(self.nb_content, f)

    def tearDown(self) -> None:
        """Cleanup temporary directory."""
        self.temp_dir.cleanup()

    def test_file_not_found(self) -> None:
        """Test that missing files raise FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            NotebookReader(Path("non_existent_file.ipynb"))

    def test_invalid_json(self) -> None:
        """Test that corrupt JSON files raise ValueError."""
        bad_path = Path(self.temp_dir.name) / "bad.ipynb"
        with open(bad_path, "w", encoding="utf-8") as f:
            f.write("{ invalid json }")

        reader = NotebookReader(bad_path)
        with self.assertRaises(ValueError):
            reader.read()

    def test_get_code_cells(self) -> None:
        """Test extraction of code cells."""
        reader = NotebookReader(self.nb_path)
        cells = reader.get_code_cells()

        self.assertEqual(len(cells), 2)
        self.assertIn("import os", cells[0])
        # Check normalization of list vs string source
        self.assertEqual(cells[1], "!pip install requests")


class TestDependencyAnalyzer(unittest.TestCase):
    """Test suite for the DependencyAnalyzer class."""

    def setUp(self) -> None:
        """Create a temporary notebook with mixed dependencies."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.nb_path = Path(self.temp_dir.name) / "deps.ipynb"

        self.nb_content = {
            "cells": [
                {
                    "cell_type": "code",
                    "source": ["import numpy as np\n", "from pandas import DataFrame"],
                },
                {
                    "cell_type": "code",
                    "source": ["%pip install seaborn\n", "!pip install -q matplotlib"],
                },
            ],
            "metadata": {},
            "nbformat": 4,
        }

        with open(self.nb_path, "w", encoding="utf-8") as f:
            json.dump(self.nb_content, f)

    def tearDown(self) -> None:
        """Cleanup."""
        self.temp_dir.cleanup()

    def test_get_all_dependencies(self) -> None:
        """Test full aggregation of dependencies."""
        reader = NotebookReader(self.nb_path)
        analyzer = DependencyAnalyzer(reader)

        deps = analyzer.get_all_dependencies()

        expected = {"numpy", "pandas", "seaborn", "matplotlib"}
        self.assertTrue(expected.issubset(deps), f"Missing deps. Found: {deps}")


if __name__ == "__main__":
    unittest.main()
