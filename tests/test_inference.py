"""
Unit tests for the inference and static analysis logic.
"""

import unittest
import libcst as cst
from lib2notebook2lib.inference import analyze_module, Scaffolder, CodeStructure


class TestInferenceAnalysis(unittest.TestCase):
    """Test suite for CST analysis logic."""

    def parse(self, code: str) -> cst.Module:
        """Helper to parse a string into CST."""
        return cst.parse_module(code.strip())

    def test_docstring_extraction(self) -> None:
        """Test extraction of top-level docstrings."""
        code = '"""My Docstring"""\nx = 1'
        tree = self.parse(code)
        struct = analyze_module(tree)
        self.assertEqual(struct.docstring, "My Docstring")
        self.assertEqual(len(struct.global_logic), 1)

    def test_import_segregation(self) -> None:
        """Test that imports are separated from logic."""
        code = """
import os
x = 10
from sys import path
        """
        tree = self.parse(code)
        struct = analyze_module(tree)
        self.assertEqual(len(struct.imports), 2)
        self.assertEqual(len(struct.global_logic), 1)
        # Check specific types
        self.assertIsInstance(struct.imports[0].body[0], cst.Import)
        self.assertIsInstance(struct.imports[1].body[0], cst.ImportFrom)

    def test_class_function_segregation(self) -> None:
        """Test that definitions are separated."""
        code = """
class A:
    pass
def b():
    pass
c = A()
        """
        tree = self.parse(code)
        struct = analyze_module(tree)
        self.assertEqual(len(struct.definitions), 2)
        self.assertEqual(len(struct.global_logic), 1)  # c = A()

    def test_main_block_extraction(self) -> None:
        """Test detection and extraction of if __name__ == '__main__'."""
        code = """
print('start')
if __name__ == "__main__":
    print('running main')
    run()
        """
        tree = self.parse(code)
        struct = analyze_module(tree)

        # Check global logic
        self.assertEqual(len(struct.global_logic), 1)  # print('start')

        # Check main block extraction
        self.assertEqual(len(struct.main_block), 2)  # print and run
        # Verify content
        first_stmt = struct.main_block[0]
        # In LibCST SimpleStatementLine contains the expr
        self.assertIsInstance(first_stmt, cst.SimpleStatementLine)

    def test_alternative_quotes_main(self) -> None:
        """Test main guard detection with single quotes."""
        code = "if __name__ == '__main__': pass"
        tree = self.parse(code)
        struct = analyze_module(tree)
        # Should be detected (extracted to main_block)
        # Pass is one statement
        self.assertEqual(len(struct.main_block), 1)
        self.assertEqual(len(struct.global_logic), 0)


class TestScaffolder(unittest.TestCase):
    """Test suite for code generation inference."""

    def test_infer_simple_args(self) -> None:
        """Test scaffolding for a function with simple arguments."""
        code = "def process(data, path): pass"
        tree = cst.parse_module(code)
        func_def = tree.body[0]

        scaffold = Scaffolder.infer_function_setup(func_def)

        self.assertIn("data = 'Replace Me'", scaffold)
        self.assertIn("path = 'Replace Me'", scaffold)
        self.assertIn("process(data, path)", scaffold)

    def test_infer_defaults_ignored(self) -> None:
        """Test that default arguments are commented out/optional."""
        code = "def config(verbose=True, limit=10): pass"
        tree = cst.parse_module(code)
        func_def = tree.body[0]

        scaffold = Scaffolder.infer_function_setup(func_def)

        self.assertIn("# verbose = ...", scaffold)
        self.assertIn("# limit = ...", scaffold)
        # Should call with no args since all are default, or we don't pass them in current logic
        self.assertIn("config()", scaffold)


if __name__ == "__main__":
    unittest.main()
