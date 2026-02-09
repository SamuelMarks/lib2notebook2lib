"""
Module for static analysis and execution inference of Python code.

Provides logic to categorize code blocks (imports, definitions, main guards)
and infer variable setups for function execution scaffolding.
"""

import libcst as cst
from typing import List, Union, Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class CodeStructure:
    """
    Container for categorized LibCST nodes extracted from a module.

    Attributes:
        docstring: The top-level module docstring, if any.
        imports: List of Import and ImportFrom nodes.
        definitions: List of ClassDef and FunctionDef nodes.
        global_logic: List of statements executed at the top level
                      (assignments, function calls, conditional logic).
        main_block: List of statements found inside `if __name__ == "__main__":`.
    """

    docstring: Optional[str] = None
    imports: List[cst.CSTNode] = field(default_factory=list)
    definitions: List[cst.CSTNode] = field(default_factory=list)
    global_logic: List[cst.CSTNode] = field(default_factory=list)
    main_block: List[cst.CSTNode] = field(default_factory=list)


class StructureVisitor(cst.CSTVisitor):
    """
    LibCST Visitor to segregate module-level code into logical buckets.
    """

    def __init__(self) -> None:
        """Initialize the visitor with an empty structure container."""
        self.structure = CodeStructure()
        self._in_top_level = True

    def visit_Module(self, node: cst.Module) -> Optional[bool]:
        """
        Entry point for the module traversal.

        Args:
            node: The module node.

        Returns:
            True to visit children.
        """
        # We manually iterate over the body in visit_Module to control extraction,
        # but LibCST visits standardly. To determine "Top Level", we track depth
        # or just iterate the body manually in the calling code?
        # A clearer approach for restructuring is manual iteration of module.body
        # inside the Transformer or Analyzer class, rather than a generic Visitor
        # recursively diving.
        # HOWEVER, sticking to the standard Visitor pattern:
        return True

    def visit_ClassDef(self, node: cst.ClassDef) -> Optional[bool]:
        """
        Captures top-level class definitions.

        Args:
            node: The class definition node.

        Returns:
            bool: False to prevent descending into methods (we treat the class as a block).
        """
        if self._in_top_level:
            self.structure.definitions.append(node)
            return False
        return True

    def visit_FunctionDef(self, node: cst.FunctionDef) -> Optional[bool]:
        """
        Captures top-level function definitions.

        Args:
            node: The function definition node.

        Returns:
            bool: False, we treat functions as opaque blocks for the notebook cell.
        """
        if self._in_top_level:
            self.structure.definitions.append(node)
            return False
        return True

    def visit_Import(self, node: cst.Import) -> Optional[bool]:
        """Captures standard imports."""
        if self._in_top_level:
            self.structure.imports.append(node)
        return False

    def visit_ImportFrom(self, node: cst.ImportFrom) -> Optional[bool]:
        """Captures from-imports."""
        if self._in_top_level:
            self.structure.imports.append(node)
        return False

    def visit_If(self, node: cst.If) -> Optional[bool]:
        """
        Detects `if __name__ == "__main__":` blocks.

        Args:
            node: The If statement node.

        Returns:
            bool: False if it's the main block (we consume it), True otherwise.
        """
        if self._in_top_level and self._is_main_guard(node):
            # Extract content of the main block
            # node.body is an IndentedBlock, we want the statements inside it
            self.structure.main_block.extend(node.body.body)
            # Do not visit children, we handled this block
            return False

        # Regular global boolean logic (e.g., configuration checks)
        if self._in_top_level:
            self.structure.global_logic.append(node)
            return False
        return True

    def _is_main_guard(self, node: cst.If) -> bool:
        """
        Checks if an If node represents the standard main execution guard.

        Matches:
            if __name__ == "__main__":
            if __name__ == '__main__':

        Args:
            node: The CST If node.

        Returns:
            True if it matches the pattern.
        """
        # We need to inspect node.test
        # Structure: Comparison(
        #   left=Name(value="__name__"),
        #   comparisons=[
        #       ComparisonTarget(
        #           operator=Equal(),
        #           comparator=SimpleString(value='"__main__"')
        #       )
        #   ]
        # )
        test = node.test
        if not isinstance(test, cst.Comparison):
            return False

        # Check Left: __name__
        if not (isinstance(test.left, cst.Name) and test.left.value == "__name__"):
            return False

        # Check Operator and Right side
        if len(test.comparisons) != 1:
            return False

        target = test.comparisons[0]
        if not isinstance(target.operator, cst.Equal):
            return False

        comparator = target.comparator
        if isinstance(comparator, cst.SimpleString):
            # Check value stripping quotes
            val = comparator.value
            clean_val = val.strip("'").strip('"')
            return clean_val == "__main__"

        return False

    def visit_SimpleStatementLine(
        self, node: cst.SimpleStatementLine
    ) -> Optional[bool]:
        """
        Captures generic statements (assignments, expressions) at top level.

        Args:
            node: The statement line node.

        Returns:
            bool: False.
        """
        # This visitor is usually called on children of Module.
        # We need to determine if this node was already handled (like imports).
        # Since visit_Import handles the specific small statement,
        # and SimpleStatementLine wraps them, we need to be careful not to double count.
        # Strategy: We assume the external Analyzer iterates Module.body and dispatches.
        # See `analyze_module` below for the robust implementation that replaces manual traversal.
        return False


def analyze_module(module: cst.Module) -> CodeStructure:
    """
    Parses a CST Module and segregates nodes into the CodeStructure container.

    Iterates over the top-level body nodes and delegates to specific checkers.

    Args:
        module: The parsed LibCST module.

    Returns:
        A populated CodeStructure object.
    """
    struct = CodeStructure()
    visitor = StructureVisitor()

    # Iterate top-level statements manually to avoid deep recursion confusion
    # and to handle the SimpleStatementLine wrapper logic cleanly.

    # 1. Check Docstring (First node)
    body = list(module.body)
    if body:
        first = body[0]
        if isinstance(first, cst.SimpleStatementLine) and len(first.body) == 1:
            expr = first.body[0]
            if isinstance(expr, cst.Expr) and isinstance(expr.value, cst.SimpleString):
                # Defines a docstring
                raw = expr.value.value
                # Simple cleaning
                if raw.startswith('"""') or raw.startswith("'''"):
                    struct.docstring = raw[3:-3].strip()
                elif raw.startswith('"') or raw.startswith("'"):
                    struct.docstring = raw[1:-1].strip()
                else:
                    struct.docstring = raw
                body.pop(0)

    for node in body:
        # Check for imports (wrapped in SimpleStatementLine)
        is_import = False
        if isinstance(node, cst.SimpleStatementLine):
            # Check the internal small statement
            first_stmt = node.body[0]
            if isinstance(first_stmt, (cst.Import, cst.ImportFrom)):
                struct.imports.append(node)
                is_import = True

        if is_import:
            continue

        # Check for Definitions
        if isinstance(node, (cst.ClassDef, cst.FunctionDef)):
            struct.definitions.append(node)
            continue

        # Check for Main Guard
        if isinstance(node, cst.If):
            if visitor._is_main_guard(node):
                # Extract body statements
                struct.main_block.extend(node.body.body)
                continue
            else:
                struct.global_logic.append(node)
                continue

        # Everything else (Assignments, Expressions, misc)
        struct.global_logic.append(node)

    return struct


class Scaffolder:
    """
    Generates inference code for determining execution flow / playground cells.
    """

    @staticmethod
    def infer_function_setup(func_node: cst.FunctionDef) -> str:
        """
        Creates a code string defining placeholder variables for a function call.

        Example:
            def foo(a, b=1): ...
            ->
            # Setup for foo
            a = ... # TODO: Define value
            # b = 1 # Default
            foo(a=a, b=b)

        Args:
            func_node: The function definition node to analyze.

        Returns:
            A string of Python code representing the setup and call.
        """
        lines = [f"# Example execution for: {func_node.name.value}"]
        args_to_pass = []

        # Process parameters
        params = func_node.params

        # 1. Positional / Keyword Arguments
        for param in params.params:
            name = param.name.value
            if param.default:
                # Has default, comment it out or show it
                # Converting default CST node back to code is complex without a transformer,
                # but valid for heuristic. We'll skip complex default values for now
                # and just assume the user wants to see the variable.
                lines.append(f"# {name} = ... # (Optional, has default)")
                # args_to_pass.append(f"{name}={name}")
                # Usually we only play with required args in a scaffold
            else:
                lines.append(f"{name} = 'Replace Me'")
                args_to_pass.append(f"{name}")

        call_str = f"{func_node.name.value}({', '.join(args_to_pass)})"
        lines.append(call_str)

        return "\n".join(lines)
