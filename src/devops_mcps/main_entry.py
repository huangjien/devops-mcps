"""Main entry point module for CLI argument parsing and execution logic.

This module contains the main() and main_stream_http() functions that handle
command-line argument parsing and server startup logic.
"""

import argparse
import logging
import os
import sys

from .server_setup import create_mcp_server, initialize_clients
from .prompt_management import load_and_register_prompts
from .mcp_tools import register_tools

# Get logger for this module
logger = logging.getLogger(__name__)


def main():
    """Entry point for the CLI."""
    # Initialize clients and validate configuration
    initialize_clients()
    
    # Create MCP server instance
    mcp = create_mcp_server()
    
    # Register all MCP tools
    register_tools(mcp)
    
    # Load and register dynamic prompts
    load_and_register_prompts(mcp)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="DevOps MCP Server (PyGithub - Raw Output)"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "stream_http"],
        default="stdio",
        help="Transport type (stdio or stream_http)",
    )
    
    args = parser.parse_args()
    
    logger.info(
        f"Starting MCP server with {args.transport} transport..."
    )
    
    # Start the server with the specified transport
    if args.transport == "stream_http":
        mcp.run(transport="streamable-http", mount_path="/mcp")
    else:
        mcp.run(transport=args.transport)


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


def setup_and_run(transport: str = "stdio", host: str = "127.0.0.1", port: int = 3721):
    """Programmatic interface to set up and run the MCP server.
    
    Args:
        transport: Transport type ('stdio' or 'http')
        host: Host address for HTTP transport
        port: Port number for HTTP transport
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
        mcp.run(transport="streamable-http", mount_path="/mcp")
    else:
        mcp.run(transport=transport)


if __name__ == "__main__":
    main()