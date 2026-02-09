"""
Tests for the Reverse Engineering module (Python -> Notebook).
"""

import unittest
import tempfile
from textwrap import dedent
from pathlib import Path
from lib2notebook2lib.reverser import LibraryToNotebook


class TestLibraryToNotebook(unittest.TestCase):
    """Test suite for LibraryToNotebook conversion logic."""

    def setUp(self) -> None:
        """Create a temporary directory."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        """Cleanup temporary resources."""
        self.temp_dir.cleanup()

    def create_py_file(self, filename: str, content: str) -> Path:
        """Helper to write a python file."""
        path = self.root / filename
        path.write_text(content, encoding="utf-8")
        return path

    def test_file_not_found(self) -> None:
        """Test validation for missing source file."""
        with self.assertRaises(FileNotFoundError):
            LibraryToNotebook(self.root / "ghost.py")

    def test_docstring_header_extraction(self) -> None:
        """Test that the module docstring becomes a Markdown cell."""
        code = dedent('"""\nMy Module\nDescription.\n"""\nimport os')
        path = self.create_py_file("doc.py", code)

        converter = LibraryToNotebook(path)
        nb = converter.convert()

        cells = nb["cells"]
        # Expected:
        # 1. Markdown (Doc)
        # 2. Code (Imports)
        self.assertEqual(len(cells), 2)

        self.assertEqual(cells[0]["cell_type"], "markdown")
        source = "".join(cells[0]["source"]).strip()
        self.assertIn("My Module", source)

    def test_structural_grouping(self) -> None:
        """
        Test the heuristic grouping order + Playground inference.
        """
        code = dedent("""
        import sys
        from os import path
        
        def my_func():
            pass
        
        class MyClass:
            pass
        
        x = 10
        print(x)
        """)
        path = self.create_py_file("structure.py", code)
        converter = LibraryToNotebook(path)
        nb = converter.convert()

        cells = nb["cells"]
        # Expected Breakdown:
        # 1. Imports (sys, os)              -> 1 Cell
        # 2. Def: my_func                   -> 1 Cell
        # 3. Def: MyClass                   -> 1 Cell
        # 4. Global Logic (x=10, print)     -> 1 Cell
        # 5. Playground Header (Inferred)   -> 1 Cell
        # 6. Playground Code (Inferred)     -> 1 Cell
        # Total: 6 Cells

        self.assertEqual(len(cells), 6)

        # Verify Imports
        self.assertIn("import sys", "".join(cells[0]["source"]))

        # Verify Definitions
        self.assertIn("def my_func", "".join(cells[1]["source"]))
        self.assertIn("class MyClass", "".join(cells[2]["source"]))

        # Verify Logic
        self.assertIn("x = 10", "".join(cells[3]["source"]))

        # Verify Playground
        self.assertIn("Interactive Playground", "".join(cells[4]["source"]))

    def test_interleaved_code_reordering(self) -> None:
        """
        Test that interleaved code gets sorted + Playground inference.
        """
        code = dedent("""
        import math
        def func():
            return 1
        
        variable = 100
        
        class Container:
            a = 1
        """)
        path = self.create_py_file("interleaved.py", code)
        converter = LibraryToNotebook(path)
        nb = converter.convert()
        cells = nb["cells"]

        # Expected Breakdown:
        # 1. Imports (import math)          -> 1 Cell
        # 2. Def: func                      -> 1 Cell
        # 3. Def: Container                 -> 1 Cell
        # 4. Logic (variable = 100)         -> 1 Cell
        # 5. Playground Header              -> 1 Cell
        # 6. Playground Code                -> 1 Cell
        # Total: 6 Cells

        self.assertEqual(len(cells), 6)

        self.assertIn("import math", "".join(cells[0]["source"]))
        self.assertIn("def func", "".join(cells[1]["source"]))
        self.assertIn("class Container", "".join(cells[2]["source"]))
        self.assertIn("variable = 100", "".join(cells[3]["source"]))

    def test_broken_syntax_handling(self) -> None:
        """Test that syntax errors result in a single dump cell."""
        code = "def broken_func( return 1"
        path = self.create_py_file("broken.py", code)

        converter = LibraryToNotebook(path)
        nb = converter.convert()

        cells = nb["cells"]
        self.assertEqual(len(cells), 1)
        self.assertEqual(cells[0]["source"][0], code)

    def test_empty_file(self) -> None:
        """Test handling of an empty file."""
        path = self.create_py_file("empty.py", "")
        converter = LibraryToNotebook(path)
        nb = converter.convert()
        # Empty file -> 0 cells
        self.assertEqual(len(nb["cells"]), 0)


if __name__ == "__main__":
    unittest.main()
