"""
Core initialization for lib2notebook2lib.

Exposes primary classes for notebook parsing and dependency extraction.
"""

from .extractor import DependencyVisitor, extract_dependencies_from_text
from .parser import NotebookReader, DependencyAnalyzer

__all__ = [
    "DependencyVisitor",
    "extract_dependencies_from_text",
    "NotebookReader",
    "DependencyAnalyzer",
]
