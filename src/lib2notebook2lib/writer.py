"""
Module for writing sanitized code to package files.

Handles cleaning of Jupyter specific syntax (magics) and coalescing
code cells into Python modules.
"""

from pathlib import Path
from typing import List
import re


class CodeSanitizer:
    """
    Utility class to clean raw notebook code strings.
    """

    @staticmethod
    def sanitize_cell(source: str) -> str:
        """
        Removes Jupyter magics and shell commands from a code block.

        Filters out:
        - Lines starting with '!' (shell commands)
        - Lines starting with '%' (magic commands)
        - Lines ending with '?' (help inspection)

        Args:
            source: The raw source string of a cell.

        Returns:
            A cleaned string suitable for a .py file.
        """
        lines = source.splitlines()
        clean_lines = []
        for line in lines:
            stripped = line.strip()
            # Remove shell commands (!pip, !ls)
            if stripped.startswith("!"):
                continue
            # Remove magics (%matplotlib, %pip)
            if stripped.startswith("%"):
                continue
            # Remove help calls (object?)
            if stripped.endswith("?"):
                continue

            clean_lines.append(line)

        return "\n".join(clean_lines)


class PackageWriter:
    """
    Writes sanitized Python code to the generate project structure.
    """

    def __init__(self, package_name: str) -> None:
        """
        Initialize with the target package name.

        Args:
            package_name: The name of the package (e.g., 'my_lib').
                          Should separate input project name from python module name if different,
                          but here we assume the python module slug (underscores).
        """
        self.package_name = package_name.replace("-", "_")

    def write_code(self, project_root: Path, code_cells: List[str]) -> None:
        """
        Sanitizes and writes code cells to the package's __init__.py.

        Args:
            project_root: The root directory of the generated project.
            code_cells: A list of raw code strings from the notebook.

        Raises:
            FileNotFoundError: If the expected source directory does not exist.
        """
        src_dir = project_root / "src" / self.package_name
        if not src_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {src_dir}")

        sanitized_blocks = []
        for cell in code_cells:
            cleaned = CodeSanitizer.sanitize_cell(cell)
            if cleaned.strip():
                sanitized_blocks.append(cleaned)

        final_content = "\n\n".join(sanitized_blocks)

        # Ensure the file ends with a newline
        if final_content and not final_content.endswith("\n"):
            final_content += "\n"

        target_file = src_dir / "__init__.py"

        # We overwrite the empty __init__.py created by the generator
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(final_content)
