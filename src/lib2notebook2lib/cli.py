"""
Command Line Interface for lib2notebook2lib.

Handles argument parsing, user interaction, and invokes the SDK to perform
conversions from Jupyter Notebooks to Python Libraries.
"""

import argparse
import sys
import logging
from pathlib import Path
from typing import List, Optional

from pydantic import ValidationError

from .schema import UserConfig
from .sdk import JupyterToPackage
from .parser import NotebookReader, DependencyAnalyzer

# Configure basic logging for CLI output
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("lib2notebook2lib")


def parse_args(args: Optional[List[str]]) -> argparse.Namespace:
    """
    Defines and parses command-line arguments.

    Args:
        args: A list of argument strings (e.g., sys.argv[1:]).
              If None, argparse uses sys.argv automatically.

    Returns:
        The populated namespace of arguments.
    """
    parser = argparse.ArgumentParser(
        description="Convert a Jupyter Notebook into a pip-installable library."
    )

    parser.add_argument(
        "notebook_path", type=Path, help="Path to the source .ipynb file."
    )

    parser.add_argument(
        "--name",
        "-n",
        type=str,
        required=True,
        help="Name of the generated python package (PyPI compliant).",
    )

    parser.add_argument(
        "--version",
        "-v",
        type=str,
        default="0.0.1",
        help="Initial version of the package (default: 0.0.1).",
    )

    parser.add_argument(
        "--author",
        type=str,
        default="Jupyter User",
        help="Author name for pyproject.toml.",
    )

    parser.add_argument(
        "--email",
        type=str,
        default="user@example.com",
        help="Author email for pyproject.toml.",
    )

    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path("."),
        help="Directory where the project folder will be created (default: current dir).",
    )

    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Overwrite the output directory if it already exists.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan dependencies and show planned output without writing files.",
    )

    return parser.parse_args(args)


def handle_dry_run(config: UserConfig) -> None:
    """
    Executes a read-only analysis of the notebook.

    Prints project configuration and detected dependencies to stdout.

    Args:
        config: The validated user configuration.
    """
    reader = NotebookReader(config.notebook_path)
    analyzer = DependencyAnalyzer(reader)
    deps = sorted(analyzer.get_all_dependencies())

    logger.info("--- Dry Run Summary ---")
    logger.info(f"Project Name: {config.project_name}")
    logger.info(f"Version:      {config.version}")
    logger.info(f"Author:       {config.author_name} <{config.author_email}>")
    logger.info(f"Output Path:  {config.output_dir / config.project_name}")
    logger.info(f"\nDetected Source Cells: {len(reader.get_code_cells())}")

    if deps:
        logger.info("\nDetected Dependencies:")
        for dep in deps:
            logger.info(f" - {dep}")
    else:
        logger.info("\nNo external dependencies detected.")


def main(args: Optional[List[str]] = None) -> int:
    """
    Main application logic.

    Parses arguments, validates inputs, and orchestrates the conversion.

    Args:
        args: Command line arguments (default: sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    parsed_args = parse_args(args)

    # 1. Check Notebook Existence early
    nb_path = parsed_args.notebook_path
    if not nb_path.exists():
        logger.error(f"Error: Notebook file not found: {nb_path}")
        return 1

    # 2. Check Overwrite Protection
    target_dir = parsed_args.output_dir / parsed_args.name
    if target_dir.exists() and not parsed_args.force and not parsed_args.dry_run:
        logger.error(f"Error: Target directory '{target_dir}' exists.")
        logger.error("Use --force to overwrite.")
        return 1

    # 3. Build SDK Configuration
    try:
        config = UserConfig(
            notebook_path=nb_path,
            project_name=parsed_args.name,
            version=parsed_args.version,
            author_name=parsed_args.author,
            author_email=parsed_args.email,
            output_dir=parsed_args.output_dir,
        )
    except ValidationError as e:
        logger.error("Configuration Error:")
        for err in e.errors():
            field = ".".join(str(x) for x in err["loc"])
            logger.error(f" - {field}: {err['msg']}")
        return 1

    # 4. Execute
    try:
        if parsed_args.dry_run:
            handle_dry_run(config)
        else:
            converter = JupyterToPackage(config)
            created_path = converter.convert()
            logger.info(f"Successfully created project at: {created_path}")
            logger.info("To install: pip install .")

    except Exception as e:
        logger.exception(f"Unexpected error during conversion: {e}")
        return 1

    return 0
