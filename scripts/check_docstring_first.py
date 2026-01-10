#!/usr/bin/env python3
"""Check that docstring is the first statement in a Python module/class/function."""

import ast
import sys


def check_docstring_first(filepath: str) -> bool:
  """Check if the first statement is a docstring.

  Args:
      filepath: Path to the Python file to check.

  Returns:
      True if docstring is first, False otherwise.
  """
  try:
    with open(filepath, "r", encoding="utf-8") as f:
      content = f.read()
  except Exception:
    return True  # Skip files that can't be read

  if not content.strip():
    return True  # Empty file is okay

  try:
    tree = ast.parse(content)
  except SyntaxError:
    return True  # Skip files with syntax errors

  if not tree.body:
    return True  # Empty AST is okay

  first_node = tree.body[0]

  # Check if first statement is a docstring (Expr with Constant)
  if isinstance(first_node, ast.Expr):
    if isinstance(first_node.value, ast.Constant):
      if isinstance(first_node.value.value, str):
        return True

  return False


def main():
  """Main entry point for the pre-commit hook."""
  filepath = sys.argv[1]
  if not check_docstring_first(filepath):
    print(f"ERROR: {filepath} - Docstring should be the first statement")
    sys.exit(1)
  sys.exit(0)


if __name__ == "__main__":
  main()
