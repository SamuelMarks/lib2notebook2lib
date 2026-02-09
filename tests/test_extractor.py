"""
Unit tests for the extraction logic in extractor.py.
"""

import unittest
from textwrap import dedent
from lib2notebook2lib.extractor import extract_dependencies_from_text


class TestExtractor(unittest.TestCase):
    """Test suite for dependency extraction logic."""

    def test_basic_imports(self) -> None:
        code = dedent(""" 
        import numpy
        import os
        import requests as req
        """)
        deps = extract_dependencies_from_text(code)
        self.assertIn("numpy", deps)
        self.assertIn("os", deps)
        self.assertIn("requests", deps)

    def test_from_imports(self) -> None:
        code = dedent(""" 
        from pandas import DataFrame
        from matplotlib.pyplot import show
        """)
        deps = extract_dependencies_from_text(code)
        self.assertIn("pandas", deps)
        self.assertIn("matplotlib", deps)

    def test_pip_commands_magic(self) -> None:
        code = dedent(""" 
        %pip install seaborn
        """)
        deps = extract_dependencies_from_text(code)
        self.assertIn("seaborn", deps)

    def test_pip_commands_shell(self) -> None:
        code = dedent(""" 
        !pip install scipy
        """)
        deps = extract_dependencies_from_text(code)
        self.assertIn("scipy", deps)

    def test_mixed_content(self) -> None:
        # Manually constructed string avoids ambiguity in indentation
        # for mixed magic/python blocks, ensuring regex matches correctly.
        code = (
            "import sys\n"
            "!pip install boto3\n"
            "\n"
            "def main():\n"
            "    import json\n"
            "    pass\n"
            "\n"
            "%pip install httpx\n"
        )
        deps = extract_dependencies_from_text(code)
        self.assertIn("sys", deps)
        self.assertIn("boto3", deps)
        self.assertIn("json", deps)
        self.assertIn("httpx", deps)

    def test_relative_imports_ignored(self) -> None:
        code = dedent(""" 
        from . import sibling
        from ..parent import something
        """)
        deps = extract_dependencies_from_text(code)
        self.assertEqual(len(deps), 0)

    def test_syntax_error_resilience(self) -> None:
        code = dedent(""" 
        !pip install pytz
        this is not valid python code
        """)
        deps = extract_dependencies_from_text(code)
        self.assertIn("pytz", deps)


if __name__ == "__main__":
    unittest.main()
