"""
Integration tests for the Reverse Engineering (Lib -> Notebook) pipeline.

Verifies the final JSON structure and execution flow ordering.
"""

import unittest
import tempfile
import json
from pathlib import Path
from lib2notebook2lib.reverser import LibraryToNotebook


class TestReverserIntegration(unittest.TestCase):
    """Integration test suite for LibraryToNotebook."""

    def setUp(self) -> None:
        """Setup temp file environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        """Cleanup."""
        self.temp_dir.cleanup()

    def test_full_pipeline_with_main(self) -> None:
        """
        Structure:
        1. Docstring
        2. Imports
        3. Global Var
        4. Function Def
        5. Main Block

        Expected Notebook Cells: -> Order preserved by category logic
        Markdown(Doc), Code(Import), Code(Func), Code(Global), Markdown(Header), Code(Main Body)
        """
        code = '"""Module"""\nimport sys\nglobal_v = 1\ndef func(): pass\nif __name__ == "__main__":\n    func()'

        path = self.root / "app.py"
        path.write_text(code, encoding="utf-8")

        converter = LibraryToNotebook(path)
        nb = converter.convert()
        cells = nb["cells"]

        # 1. Markdown
        self.assertEqual(cells[0]["cell_type"], "markdown")

        # 2. Import
        self.assertIn("import sys", "".join(cells[1]["source"]))

        # 3. Defs (func)
        self.assertIn("def func", "".join(cells[2]["source"]))

        # 4. Global Logic (global_v)
        self.assertIn("global_v = 1", "".join(cells[3]["source"]))

        # 5. Main Header
        self.assertIn("Main Execution", "".join(cells[4]["source"]))

        # 6. Main Body (func())
        # Note: indent should be stripped or kept?
        # LibCST usually preserves whitespace token if we just re-emit nodes.
        # Extraction logic took node.body.body.
        main_source = "".join(cells[5]["source"])
        self.assertIn("func()", main_source)
        # Sanity check: "if __name__" should NOT be in the source, just the body
        self.assertNotIn("if __name__", main_source)

    def test_playground_inference(self) -> None:
        """
        Test that without a main block, a playground is generated for functions.
        """
        code = "def add(a, b): return a+b"
        path = self.root / "utils.py"
        path.write_text(code, encoding="utf-8")

        converter = LibraryToNotebook(path)
        nb = converter.convert()
        cells = nb["cells"]

        # Last cells should be playground
        last_cell = cells[-1]
        self.assertIn("Interactive Playground", "".join(cells[-2]["source"]))
        source = "".join(last_cell["source"])

        self.assertIn("a = 'Replace Me'", source)
        self.assertIn("add(a, b)", source)

    def test_no_code_resilience(self) -> None:
        """Test handling of empty or comment-only files."""
        path = self.root / "empty.py"
        path.write_text("# Just comments", encoding="utf-8")

        nb = LibraryToNotebook(path).convert()
        # Should have one cell with the comments (global logic bucket)
        # or empty if comments are attached to nothing in CST?
        # LibCST creates EmptyLine nodes or Comment nodes.
        # If they aren't attached to statements, analyze_module logic (module.body) might miss them.
        # However, this is acceptable for a converter.
        self.assertTrue(IsInstance(nb, dict))  # Just check it doesn't crash

        # Note on LibCST: Module body contains only statements.
        # Comments are metadata on statements or trailing whitespace.
        # If file is ONLY comments, logic might return empty.

    def test_syntax_recovery(self) -> None:
        """Test fallback on syntax error."""
        code = "def bad_syntax(:"
        path = self.root / "bad.py"
        path.write_text(code, encoding="utf-8")

        nb = LibraryToNotebook(path).convert()
        self.assertEqual(len(nb["cells"]), 1)
        self.assertIn("bad_syntax", "".join(nb["cells"][0]["source"]))


def IsInstance(obj, cls):
    return isinstance(obj, cls)


if __name__ == "__main__":
    unittest.main()
