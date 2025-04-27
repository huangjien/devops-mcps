import logging
import os
from typing import Dict, Any
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


class MCPClient:
  def __init__(self):
    """Initialize the MCP client with configuration from environment variables."""
    # Load configuration from environment variables
    self.host = os.getenv("MCP_HOST", "localhost")
    self.port = int(os.getenv("MCP_PORT", "8000"))

    # Initialize FastMCP client
    self.mcp = FastMCP(
      name="DevOps MCP Client",
      host=self.host,
      port=self.port,
      settings={"initialization_timeout": 10, "request_timeout": 300},
    )
    logger.debug(f"MCP Client initialized with host={self.host}, port={self.port}")

  async def process(self, query: str) -> str:
    """Process a natural language query and return markdown-formatted results.

    Args:
        query: The natural language query to process.

    Returns:
        A markdown-formatted string containing the query results.

    Raises:
        RuntimeError: If there's an error processing the query.
    """
    try:
      # List available tools from the MCP server
      tools = await self.mcp.list_tools()

      # Find the most appropriate tool for the query based on description matching
      selected_tool = None
      max_relevance = 0

      for tool in tools:
        if "description" in tool:
          # Simple relevance scoring based on word overlap
          query_words = set(query.lower().split())
          desc_words = set(tool["description"].lower().split())
          relevance = len(query_words.intersection(desc_words))

          if relevance > max_relevance:
            max_relevance = relevance
            selected_tool = tool

      if not selected_tool:
        return "## Error\n\nNo suitable tool found for the query."

      # Execute the selected tool
      logger.debug(f"Executing tool '{selected_tool['name']}' with query: {query}")
      result = await self.mcp.execute_tool(selected_tool["name"], query) # Pass the raw query string

      # Convert the result to markdown format
      if isinstance(result, dict):
        return self._format_dict_as_markdown(result)
      elif isinstance(result, list):
        return self._format_list_as_markdown(result)
      else:
        return str(result)

    except Exception as e:
      logger.error(f"Error processing query: {e}", exc_info=True)
      raise RuntimeError(f"Failed to process query: {e}") from e

  def _format_dict_as_markdown(self, data: Dict[str, Any]) -> str:
    """Convert a dictionary to markdown format."""
    if "error" in data:
      return f"## Error\n\n{data['error']}"

    markdown = ["## Results\n"]
    for key, value in data.items():
      markdown.append(f"### {key}\n")
      markdown.append(f"{value}\n")

    return "\n".join(markdown)

  def _format_list_as_markdown(self, data: list) -> str:
    """Convert a list to markdown format."""
    if not data:
      return "## Results\n\nNo results found."

    markdown = ["## Results\n"]
    for item in data:
      if isinstance(item, dict):
        markdown.append(self._format_dict_as_markdown(item))
      else:
        markdown.append(f"- {item}\n")

    return "\n".join(markdown)
