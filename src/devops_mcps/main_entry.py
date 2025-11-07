"""Main entry point module for CLI argument parsing and execution logic.

This module contains the main() and main_stream_http() functions that handle
command-line argument parsing and server startup logic.
"""

import argparse
import logging
import sys
from importlib.metadata import version, PackageNotFoundError

from .server_setup import create_mcp_server, initialize_clients
from .prompt_management import load_and_register_prompts
from .mcp_tools import register_tools

# Get logger for this module
logger = logging.getLogger(__name__)


def _configure_logging(level: str | None) -> None:
  """Optionally configure logging level.

  Args:
      level: One of 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'. If None, no change.
  """
  if not isinstance(level, str):
    return
  normalized = level.upper()
  levels = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
  }
  logging.getLogger().setLevel(levels.get(normalized, logging.INFO))


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
  """Build and parse CLI arguments with safe defaults."""
  parser = argparse.ArgumentParser(
    description="DevOps MCP Server (PyGithub - Raw Output)"
  )
  parser.add_argument(
    "--transport",
    choices=["stdio", "stream_http"],
    default="stdio",
    help="Transport type (stdio or stream_http)",
  )
  parser.add_argument(
    "--mount-path",
    default="/mcp",
    help="Mount path for stream_http transport (default: /mcp)",
  )
  parser.add_argument(
    "--log-level",
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    help="Optional logging level override",
  )
  parser.add_argument(
    "--version",
    action="store_true",
    help="Print package version and exit",
  )
  # Prefer parse_args to allow tests to patch it; fallback to parse_known_args
  try:
    return parser.parse_args(argv)
  except SystemExit:
    return parser.parse_known_args(argv)[0]


def main():
  """Entry point for the CLI."""
  # Parse command line arguments early to allow logging/version handling
  args = _parse_args()

  # Optional logging configuration
  _configure_logging(getattr(args, "log_level", None))

  # Version handling: print and exit early if requested
  # Only treat explicitly-set boolean True as version flag
  if getattr(args, "version", False) is True:
    try:
      pkg_version = version("devops-mcps")
    except PackageNotFoundError:
      pkg_version = "unknown"
    print(pkg_version)
    return

  # Initialize clients and validate configuration
  initialize_clients()

  # Create MCP server instance
  mcp = create_mcp_server()

  # Register all MCP tools
  register_tools(mcp)

  # Load and register dynamic prompts
  load_and_register_prompts(mcp)

  # Log startup intent
  logger.info(f"Starting MCP server with {args.transport} transport...")

  # Start the server with the specified transport
  try:
    if args.transport == "stream_http":
      mount_path = getattr(args, "mount_path", "/mcp")
      if not isinstance(mount_path, str) or not mount_path.startswith("/"):
        mount_path = "/mcp"
      mcp.run(transport="streamable-http", mount_path=mount_path)
    else:
      mcp.run(transport=args.transport)
  except KeyboardInterrupt:
    logger.info("MCP server interrupted by user (KeyboardInterrupt). Shutting down.")
    raise
  except Exception as e:
    # Log and re-raise to preserve existing test expectations
    logger.error(f"MCP server failed to start: {e}", exc_info=True)
    raise


def main_stream_http():
  """Run the MCP server with stream_http transport."""
  if "--transport" not in sys.argv:
    sys.argv.extend(["--transport", "stream_http"])
  elif "stream_http" not in sys.argv:
    try:
      idx = sys.argv.index("--transport")
      if idx + 1 < len(sys.argv):
        sys.argv[idx + 1] = "stream_http"
      else:
        sys.argv.append("stream_http")
    except ValueError:
      sys.argv.extend(["--transport", "stream_http"])

  main()


def setup_and_run(
  transport: str = "stdio",
  host: str = "127.0.0.1",
  port: int = 3721,
  mount_path: str = "/mcp",
):
  """Programmatic interface to set up and run the MCP server.

  Args:
      transport: Transport type ('stdio' or 'http')
      host: Host address for HTTP transport
      port: Port number for HTTP transport
      mount_path: Mount path for HTTP transport (default: /mcp)
  """
  # Initialize clients and validate configuration
  initialize_clients()

  # Create MCP server instance
  mcp = create_mcp_server()

  # Register all MCP tools
  register_tools(mcp)

  # Load and register dynamic prompts
  load_and_register_prompts(mcp)

  logger.info(f"Starting MCP server with {transport} transport...")

  # Start the server
  if transport == "http":
    # Preserve existing behavior while allowing optional mount_path parameter
    if not isinstance(mount_path, str) or not mount_path.startswith("/"):
      mount_path = "/mcp"
    mcp.run(transport="streamable-http", mount_path=mount_path)
  else:
    mcp.run(transport=transport)


if __name__ == "__main__":
  main()
