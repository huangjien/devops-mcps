#!/usr/bin/env python3
"""Check that Python files can be parsed (valid AST)."""

import ast
import sys


def check_ast(filepath: str) -> bool:
  """Check if Python file has valid AST.

  Args:
      filepath: Path to the Python file to check.

  Returns:
      True if AST is valid, False otherwise.
  """
  try:
    with open(filepath, "r", encoding="utf-8") as f:
      content = f.read()
    ast.parse(content)
    return True
  except SyntaxError as e:
    print(f"ERROR: {filepath}:{e.lineno}:{e.offset} - {e.msg}")
    return False
  except Exception as e:
    print(f"ERROR: {filepath} - {e}")
    return False


def main():
  """Main entry point for pre-commit hook."""
  filepath = sys.argv[1]
  if not check_ast(filepath):
    sys.exit(1)
  sys.exit(0)


if __name__ == "__main__":
  main()
