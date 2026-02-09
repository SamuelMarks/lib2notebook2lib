"""
Module for parsing Jupyter Notebook files (.ipynb).

Handles JSON loading and orchestration of dependency extraction using
the extractor module.
"""

import json
import logging
from pathlib import Path
from typing import List, Set, Any, Dict
from .extractor import extract_dependencies_from_text

# Configure a module-level logger
logger = logging.getLogger(__name__)


class NotebookReader:
    """
    Reads a Jupyter Notebook file and extracts raw code sources.
    """

    def __init__(self, filepath: Path) -> None:
        """
        Initializes the reader with the path to the notebook.

        Args:
            filepath: Path object pointing to the .ipynb file.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        if not filepath.exists():
            raise FileNotFoundError(f"Notebook not found: {filepath}")
        self.filepath = filepath

    def read(self) -> Dict[str, Any]:
        """
        Loads the JSON content of the notebook.

        Returns:
            A dictionary representing the raw notebook JSON.

        Raises:
            ValueError: If the file is not valid JSON.
        """
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in notebook: {self.filepath}") from exc

    def get_code_cells(self) -> List[str]:
        """
        Extracts the source code from all cells of type 'code'.

        Returns:
            A list of strings, where each string is the content of a code cell.
        """
        data = self.read()
        cells = data.get("cells", [])
        code_sources = []

        for cell in cells:
            if cell.get("cell_type") == "code":
                source_lines = cell.get("source", [])
                # Jupyter JSON source can be a list of strings or a single string
                if isinstance(source_lines, list):
                    code_sources.append("".join(source_lines))
                elif isinstance(source_lines, str):
                    code_sources.append(source_lines)

        return code_sources


class DependencyAnalyzer:
    """
    Orchestrates dependency detection across an entire notebook.
    """

    def __init__(self, reader: NotebookReader) -> None:
        """
        Initializes the analyzer.

        Args:
            reader: A configured NotebookReader instance.
        """
        self.reader = reader

    def get_all_dependencies(self) -> Set[str]:
        """
        Scans all code cells in the notebook for imports and install commands.

        Returns:
            A set of detected library names (e.g. {'numpy', 'pandas'}).
        """
        code_cells = self.reader.get_code_cells()
        all_deps = set()

        for code in code_cells:
            if not code.strip():
                continue

            deps = extract_dependencies_from_text(code)
            all_deps.update(deps)

        # Filter out standard library modules implicitly if desired,
        # or rely on `hatch-requirements-txt` to resolve them later.
        # For this core logic, we return what was found.
        return all_deps
