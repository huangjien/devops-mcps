import click
import logging
import sys
import asyncio  # Add asyncio import
from dotenv import load_dotenv

# Import the actual MCP client
from devops_mcps.client import MCPClient  # Use absolute import

# Setup basic logging
logging.basicConfig(
  level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


# --- Actual MCP Client Interaction Logic ---
async def process_query(query: str) -> str:
  """
  Processes the natural language query using an MCP client which interacts
  with an LLM and executes necessary MCP server calls.
  """
  logger.info(f"Processing query with MCP client: '{query}'")

  # 1. Initialize the MCP Client instance
  #    Load necessary configuration (e.g., API keys) from environment
  try:
    # Assuming MCPClient takes necessary config from env vars internally or via args
    # Adjust initialization as needed based on your MCPClient implementation
    mcp_client = MCPClient()
    logger.debug("MCP Client initialized.")
  except Exception as e:
    logger.error(f"Failed to initialize MCP Client: {e}", exc_info=True)
    # Re-raise a more specific or user-friendly exception if desired
    raise RuntimeError(f"MCP Client initialization failed: {e}") from e

  # 2. Send the query to the client for processing (asynchronously)
  try:
    # Assuming the client has an async 'process' method
    markdown_result = await mcp_client.process(query)
    logger.info("Successfully processed query via MCP client.")
    return markdown_result
  except Exception as e:
    logger.error(f"Error during MCP client processing: {e}", exc_info=True)
    # Re-raise a more specific or user-friendly exception if desired
    raise RuntimeError(f"Error processing query via MCP client: {e}") from e


# --- Placeholder Implementation ---
# Remove this section once you have a real MCPClient
# logger.warning("Using placeholder implementation for process_query.")
# return f"""
# ## Query Processed (Placeholder)
#
# Received query: "{query}"
#
# _(This is a placeholder response. Implement the actual MCP client interaction above.)_
# """


@click.command()
@click.argument("query", type=str)
@click.option("--verbose", is_flag=True, help="Enable verbose logging.")
def main(query: str, verbose: bool):
  """
  DevOps MCP CLI - Query DevOps information using natural language.

  QUERY: The natural language query (e.g., "list recent failed Jenkins builds").
  """
  if verbose:
    # Set root logger level to DEBUG
    logging.getLogger().setLevel(logging.DEBUG)
    # Ensure handler level is also DEBUG if it was set higher
    for handler in logging.getLogger().handlers:
      handler.setLevel(logging.DEBUG)
    logger.debug("Verbose logging enabled.")

  logger.info(f"Received query: '{query}'")

  try:
    # Run the async function using asyncio.run()
    markdown_result = asyncio.run(process_query(query))
    click.echo(markdown_result)
  except Exception as e:
    logger.error(f"An error occurred during query processing: {e}", exc_info=True)
    # Output a user-friendly error message to stderr
    click.echo(f"Error: {e}", err=True)
    sys.exit(1)  # Exit with a non-zero status code to indicate failure


if __name__ == "__main__":
  main()
