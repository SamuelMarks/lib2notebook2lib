"""
Unit tests for the code writing/sanitization logic.
"""

import unittest
import tempfile
from pathlib import Path
from lib2notebook2lib.writer import PackageWriter, CodeSanitizer


class TestCodeSanitizer(unittest.TestCase):
    """Test suite for CodeSanitizer static methods."""

    def test_sanitize_clean_code(self) -> None:
        """Test that normal code is untouched."""
        code = "import os\nx = 1"
        cleaned = CodeSanitizer.sanitize_cell(code)
        self.assertEqual(code, cleaned)

    def test_remove_magics(self) -> None:
        """Test removal of % magic commands."""
        code = """
        import numpy
        %matplotlib inline
        x = 10
        """
        cleaned = CodeSanitizer.sanitize_cell(code).strip()
        expected = "import numpy\n        \n        x = 10"
        # Note: Splitlines keeps indentation if lines are just skipped.
        # Refined check:
        lines = [l.strip() for l in cleaned.splitlines() if l.strip()]
        self.assertEqual(lines, ["import numpy", "x = 10"])

    def test_remove_shell(self) -> None:
        """Test removal of ! shell commands."""
        code = "!pip install pandas\nimport pandas as pd"
        cleaned = CodeSanitizer.sanitize_cell(code)
        self.assertNotIn("!pip", cleaned)
        self.assertIn("import pandas", cleaned)

    def test_remove_help(self) -> None:
        """Test removal of help inspections."""
        code = "pd.DataFrame?\ndf = pd.DataFrame()"
        cleaned = CodeSanitizer.sanitize_cell(code)
        self.assertNotIn("?", cleaned)
        self.assertIn("df =", cleaned)


class TestPackageWriter(unittest.TestCase):
    """Test suite for PackageWriter."""

    def setUp(self) -> None:
        """Create temp directory and dummy package structure."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        # Mimic structure created by scaffold
        self.pkg_name = "test_pkg"
        self.src_dir = self.root / "src" / self.pkg_name
        self.src_dir.mkdir(parents=True)
        (self.src_dir / "__init__.py").touch()

    def tearDown(self) -> None:
        """Cleanup."""
        self.temp_dir.cleanup()

    def test_write_missing_dir(self) -> None:
        """Test error when source directory is missing."""
        writer = PackageWriter("non_existent")
        with self.assertRaises(FileNotFoundError):
            writer.write_code(self.root, [])

    def test_write_code_flow(self) -> None:
        """Test valid writing of sanitized code to __init__.py."""
        cells = ["import os\n!ls", "def foo():\n    return 1", "%timeit foo()"]

        writer = PackageWriter(self.pkg_name)
        writer.write_code(self.root, cells)

        target = self.src_dir / "__init__.py"
        content = target.read_text(encoding="utf-8")

        self.assertIn("import os", content)
        self.assertIn("def foo():", content)
        self.assertNotIn("!ls", content)
        self.assertNotIn("%timeit", content)

        # Check concatenation spacing
        self.assertIn("\n\n", content)


if __name__ == "__main__":
    unittest.main()
