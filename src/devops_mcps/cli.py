#!/usr/bin/env python3
"""
Command-line interface for MCP client.
"""

import argparse
import asyncio
from .client import MCPClient


async def main():
  parser = argparse.ArgumentParser(description="MCP Client Command Line Interface")

  # Server configuration
  parser.add_argument(
    "--server",
    default="http://localhost:8000",
    help="MCP server URL (default: http://localhost:8000)",
  )

  # Command modes
  subparsers = parser.add_subparsers(dest="command", required=True)

  # Direct tool call mode
  tool_parser = subparsers.add_parser("tool", help="Call MCP tool directly")
  tool_parser.add_argument("tool_name", help="Name of the MCP tool to call")
  tool_parser.add_argument(
    "--args", default="{}", help="JSON string of arguments (default: {})"
  )

  # Natural language mode
  nl_parser = subparsers.add_parser("nl", help="Process natural language query")
  nl_parser.add_argument("--query", help="Natural language query to process")
  nl_parser.add_argument("query_positional", nargs='?', help="Natural language query (positional)")

  args = parser.parse_args()

  client = MCPClient(args.server)

  try:
    if args.command == "tool":
      import json

      tool_args = json.loads(args.args)
      result = await client.call_mcp_server(args.tool_name, tool_args)
    elif args.command == "nl":
      query = args.query if args.query else args.query_positional
      if not query:
        raise ValueError("Query must be provided either as --query or positional argument")
      result = await client.process_natural_language(query)

    print(result)
  except Exception as e:
    print(f"Error: {str(e)}")


if __name__ == "__main__":
  asyncio.run(main())
