"""
Module for converting Python source files (.py) into Jupyter Notebooks (.ipynb).

Utilizes LibCST and the inference module to structurally organize code into
documentation, imports, definitions, global variables, and execution blocks.
"""

import libcst as cst
from pathlib import Path
from typing import List, Dict, Any, Union

from .inference import analyze_module, Scaffolder, CodeStructure


class LibraryToNotebook:
    """
    Reverse engineering engine to convert a Python library file into a structured Jupyter Notebook.
    """

    def __init__(self, source_path: Path) -> None:
        """
        Initialize the converter with the path to the python file.

        Args:
            source_path: Path object pointing to the .py file to convert.

        Raises:
            FileNotFoundError: If the source file does not exist.
        """
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        self.source_path = source_path

    def _read_source(self) -> str:
        """Reads the content of the source file."""
        return self.source_path.read_text(encoding="utf-8")

    def _create_cell(self, cell_type: str, source: str) -> Dict[str, Any]:
        """
        Constructs a Jupyter Notebook cell dictionary.

        Args:
            cell_type: 'code' or 'markdown'.
            source: Content string.

        Returns:
            NBFormat cell dictionary.
        """
        # Ensure newline at end of list items for proper JSON format usually
        # But splitlines(keepends=True) handles it.
        lines = source.splitlines(keepends=True)
        # Handle case where source is empty
        if not lines:
            lines = []

        cell = {"cell_type": cell_type, "metadata": {}, "source": lines}
        if cell_type == "code":
            cell["execution_count"] = None
            cell["outputs"] = []
        return cell

    def convert(self) -> Dict[str, Any]:
        """
        Parses the Python file and reconstructs it as a Notebook JSON object.

        Structural Flow:
        1. Module Docstring (Markdown)
        2. Imports (Code)
        3. Definitions (Code - one cell per class/func)
        4. Global Logic (Code - assignments, constants)
        5. Execution Inference (Code)
           - If `if __name__ == "__main__":` exists, that is the run cell.
           - Else, if functions exist, generate a "Playground" scaffold.

        Returns:
            A dictionary representing the Jupyter Notebook (nbformat v4).
        """
        source_text = self._read_source()

        try:
            tree = cst.parse_module(source_text)
        except cst.ParserSyntaxError:
            # Fallback for syntax errors
            return self._wrap_in_notebook([self._create_cell("code", source_text)])

        # Analyze structure using inference module
        struct = analyze_module(tree)

        cells: List[Dict[str, Any]] = []

        # 1. Docstring
        if struct.docstring:
            cells.append(self._create_cell("markdown", struct.docstring))

        # 2. Imports
        if struct.imports:
            code = cst.Module(body=struct.imports).code
            cells.append(self._create_cell("code", code))

        # 3. Definitions
        # Create separate cells for each definition for better readability
        # Just wrap each node in a module to print it
        for dfn in struct.definitions:
            # Create a localized module to generate code for just this node
            # We must pass list of statements
            wrapper = cst.Module(body=[dfn])
            cells.append(self._create_cell("code", wrapper.code))

        # 4. Global Logic (Constants, Side effects on import)
        if struct.global_logic:
            code = cst.Module(body=struct.global_logic).code
            cells.append(self._create_cell("code", code))

        # 5. Execution Logic
        # Priority: Main Block > Scaffolding
        if struct.main_block:
            # We have an explicit run block
            # Add a markdown header? Optional, but nice.
            cells.append(self._create_cell("markdown", "### Main Execution"))
            code = cst.Module(body=struct.main_block).code
            cells.append(self._create_cell("code", code))
        elif struct.definitions:
            # No main block, but we have definitions.
            # Generate a scaffold for the last defined function as a playground
            # Find last function def
            funcs = [n for n in struct.definitions if isinstance(n, cst.FunctionDef)]
            if funcs:
                target_func = funcs[-1]
                scaffold_code = Scaffolder.infer_function_setup(target_func)
                cells.append(
                    self._create_cell(
                        "markdown", "### Interactive Playground (Inferred)"
                    )
                )
                cells.append(self._create_cell("code", scaffold_code))

        return self._wrap_in_notebook(cells)

    def _wrap_in_notebook(self, cells: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Wraps cells in NBFormat headers."""
        return {
            "cells": cells,
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3",
                },
                "language_info": {
                    "codemirror_mode": {"name": "ipython", "version": 3},
                    "file_extension": ".py",
                    "mimetype": "text/x-python",
                    "name": "python",
                    "nbconvert_exporter": "python",
                    "pygments_lexer": "ipython3",
                    "version": "3.8.0",
                },
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        }
