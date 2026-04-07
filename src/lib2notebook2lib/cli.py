"""
Command Line Interface for lib2notebook2lib.

Handles argument parsing, user interaction, and invokes the SDK to perform
conversions from Jupyter Notebooks to Python Libraries.
"""

import argparse
import sys
import json
import logging
from pathlib import Path
from typing import List, Optional

import libcst as cst
from pydantic import ValidationError

from .schema import UserConfig
from .sdk import JupyterToPackage
from .parser import NotebookReader, DependencyAnalyzer
from .reverser import LibraryToNotebook

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
        "notebook_path",
        type=Path,
        nargs="?",
        help="Path to the source .ipynb file (Legacy mode).",
    )

    parser.add_argument(
        "--name",
        "-n",
        type=str,
        help="Name of the generated python package (PyPI compliant). Required for legacy mode.",
    )

    parser.add_argument(
        "--audit",
        nargs="+",
        type=Path,
        help="Audit the specified files (verify they are valid notebooks or python files).",
    )

    parser.add_argument(
        "--fix",
        nargs="+",
        type=Path,
        help="Fix/Convert the specified files (.ipynb -> package, .py -> .ipynb).",
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


def handle_audit(paths: List[Path]) -> int:
    """
    Validates that the given files are well-formed notebooks or python files.

    Args:
        paths: A list of file paths to audit.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    has_error = False
    for path in paths:
        if not path.exists():
            logger.error(f"Error: Path does not exist: {path}")
            has_error = True
            continue

        try:
            if path.suffix == ".ipynb":
                NotebookReader(path)
                logger.info(f"Audit passed: {path}")
            elif path.suffix == ".py":
                # Ensure we can parse it as a valid python module using CST
                source = path.read_text(encoding="utf-8")
                cst.parse_module(source)
                logger.info(f"Audit passed: {path}")
            else:
                logger.error(f"Error: Unsupported file type for audit: {path}")
                has_error = True
        except Exception as e:
            logger.error(f"Audit failed for {path}: {e}")
            has_error = True

    return 1 if has_error else 0


def handle_fix(
    paths: List[Path], dry_run: bool, version: str, author: str, email: str, force: bool
) -> int:
    """
    Converts notebooks to packages or python files to notebooks.

    Args:
        paths: A list of file paths to fix.
        dry_run: If True, prints intended actions without writing to disk.
        version: Package version (used for notebook to package conversion).
        author: Author name (used for notebook to package conversion).
        email: Author email (used for notebook to package conversion).
        force: If True, overwrites existing output directories or files.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    has_error = False
    for path in paths:
        if not path.exists():
            logger.error(f"Error: Path does not exist: {path}")
            has_error = True
            continue

        try:
            if path.suffix == ".ipynb":
                project_name = path.stem
                output_dir = path.parent
                target_dir = output_dir / project_name

                if target_dir.exists() and not force and not dry_run:
                    logger.error(
                        f"Error: Target directory '{target_dir}' exists. Use --force."
                    )
                    has_error = True
                    continue

                if dry_run:
                    logger.info(
                        f"[Dry Run] Would convert {path} to package '{project_name}' at {target_dir}"
                    )
                else:
                    config = UserConfig(
                        notebook_path=path,
                        project_name=project_name,
                        version=version,
                        author_name=author,
                        author_email=email,
                        output_dir=output_dir,
                    )
                    converter = JupyterToPackage(config)
                    created_path = converter.convert()
                    logger.info(f"Successfully created project at: {created_path}")

            elif path.suffix == ".py":
                target_path = path.with_suffix(".ipynb")
                if target_path.exists() and not force and not dry_run:
                    logger.error(
                        f"Error: Target file '{target_path}' exists. Use --force."
                    )
                    has_error = True
                    continue

                if dry_run:
                    logger.info(
                        f"[Dry Run] Would convert {path} to notebook at {target_path}"
                    )
                else:
                    converter = LibraryToNotebook(path)
                    notebook_dict = converter.convert()
                    with open(target_path, "w", encoding="utf-8") as f:
                        json.dump(notebook_dict, f, indent=2)
                    logger.info(f"Successfully created notebook at: {target_path}")

            else:
                logger.error(f"Error: Unsupported file type for fix: {path}")
                has_error = True

        except Exception as e:
            logger.error(f"Fix failed for {path}: {e}")
            has_error = True

    return 1 if has_error else 0


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

    if parsed_args.audit:
        return handle_audit(parsed_args.audit)

    if parsed_args.fix:
        return handle_fix(
            parsed_args.fix,
            parsed_args.dry_run,
            parsed_args.version,
            parsed_args.author,
            parsed_args.email,
            parsed_args.force,
        )

    if not parsed_args.notebook_path or not parsed_args.name:
        logger.error(
            "Error: --name and notebook_path are required for legacy conversion mode."
        )
        return 1

    # Legacy Mode
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
