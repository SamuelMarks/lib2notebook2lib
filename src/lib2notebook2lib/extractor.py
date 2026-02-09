"""
Module responsible for extracting dependencies from code strings.

Uses LibCST for Python AST traversal to detect imports, and Regular Expressions
to detect Jupyter magic commands and shell pip installs.
"""

import re
import libcst as cst
from typing import Set, List, Optional, Union


class DependencyVisitor(cst.CSTVisitor):
    """
    LibCST Visitor to extract imported module names from Python code.

    Attributes:
        found_imports (Set[str]): A set of unique top-level module names found
            during traversal.
    """

    def __init__(self) -> None:
        """
        Initializes the visitor with an empty set of imports.
        """
        self.found_imports: Set[str] = set()

    def _add_module(self, module_name: Optional[str]) -> None:
        """
        Helper validation to add a module to the found set.

        Args:
            module_name: The name of the module to add. If None or relative
                (starts with dot), it is ignored.
        """
        if module_name and not module_name.startswith("."):
            # We only care about the top-level package for requirements.txt
            # e.g., 'matplotlib.pyplot' -> 'matplotlib'
            top_level = module_name.split(".")[0]
            if top_level:
                self.found_imports.add(top_level)

    def _get_full_name(self, node: Union[cst.Name, cst.Attribute]) -> str:
        """
        Recursively reconstructs the full dotted name from a CST node.
        """
        if isinstance(node, cst.Name):
            return node.value
        elif isinstance(node, cst.Attribute):
            return f"{self._get_full_name(node.value)}.{node.attr.value}"
        return ""

    def visit_Import(self, node: cst.Import) -> None:
        """
        Visits an `import` statement (e.g., `import numpy`).
        """
        for alias in node.names:
            # alias.name.value could be "numpy.linalg"
            name_node = alias.name
            full_name = self._get_full_name(name_node)
            self._add_module(full_name)

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        """
        Visits a `from ... import` statement.
        """
        # Check for relative imports (e.g. from . import sibling)
        if len(node.relative) > 0:
            return

        if node.module:
            module_struct = node.module
            full_name = self._get_full_name(module_struct)
            self._add_module(full_name)


def _extract_pip_commands(line: str) -> Set[str]:
    """
    Scans a single line for pip install commands.

    Detects:
    - !pip install package
    - %pip install package
    - !python -m pip install package
    - !python3 -m pip install package
    """
    pkg_set = set()
    line = line.strip()

    # Matches: (!|%)pip install ... OR !python[3?] -m pip install ...
    pattern = r"^(?:!|%)?(?:pip|python(?:3)?\s+-m\s+pip)\s+install\s+(.+)$"
    match = re.match(pattern, line)

    if match:
        args_str = match.group(1)
        tokens = args_str.split()
        for token in tokens:
            if token.startswith("-"):
                continue
            # Filter out tokens that look like URLs or paths.
            # Removed the check for "http" string to allow packages like 'httpx'.
            if "/" in token or ".git" in token:
                continue

            clean_name = re.split(r"[=<>!]", token)[0]
            if clean_name:
                pkg_set.add(clean_name)

    return pkg_set


def extract_dependencies_from_text(source_text: str) -> Set[str]:
    """
    Analyzes a block of text (combining shell and python) for dependencies.
    """
    dependencies = set()

    lines = source_text.splitlines()
    clean_python_lines = []

    for line in lines:
        stripped = line.strip()
        # Handle Magics / Shell
        if stripped.startswith("!") or stripped.startswith("%"):
            pip_deps = _extract_pip_commands(stripped)
            dependencies.update(pip_deps)
            continue

        if stripped.endswith("?"):
            continue

        clean_python_lines.append(line)

    clean_source = "\n".join(clean_python_lines)

    if clean_source.strip():
        try:
            tree = cst.parse_module(clean_source)
            visitor = DependencyVisitor()
            tree.visit(visitor)
            dependencies.update(visitor.found_imports)
        except cst.ParserSyntaxError:
            pass

    return dependencies
