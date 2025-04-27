import os
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import httpx  # Ensure httpx is imported

# MCP imports
from mcp.server.fastmcp import FastMCP


class FastMCP:
    """
    FastMCP client class for connecting to MCP server.
    """

    def __init__(self, server_url: str):
        self.server_url = server_url
        self._client = None

    async def __aenter__(self):
        """Enter async context manager."""
        import httpx
        self._client = httpx.AsyncClient(base_url=self.server_url)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        if self._client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)

    @classmethod
    async def connect(cls, server_url: str):
        """
        Connect to MCP server.

        Args:
            server_url: URL of the MCP server

        Returns:
            FastMCP client instance that supports async context manager
        """
        instance = cls(server_url)
        # The async with statement will handle calling __aenter__
        return instance

    async def list_tools(self) -> Dict[str, Any]:
        """List available tools from the MCP server."""
        if not self._client:
            logger.error("Attempted to list tools, but client is not connected.")
            raise ConnectionError("Client not connected")
        try:
            logger.debug(f"Requesting tool list from {self.server_url}/tools")
            response = await self._client.get("/tools")
            logger.debug(f"Received response status: {response.status_code}")
            # Log raw response text (truncated) for debugging non-JSON or error responses
            try:
                raw_text = response.text[:500] # Log first 500 chars
                logger.debug(f"Raw response text (truncated): {raw_text}")
            except Exception as text_ex:
                logger.debug(f"Could not get raw response text: {text_ex}")

            response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred while listing tools: {e.response.status_code} - {e.response.text}")
            raise  # Re-raise the specific HTTP error
        except httpx.RequestError as e:
            # Catches connection errors, timeout errors, protocol errors etc.
            logger.error(f"Network error occurred while listing tools: {type(e).__name__} - {str(e)}")
            # Log specific details for common errors if helpful
            if isinstance(e, httpx.RemoteProtocolError):
                logger.error("Server disconnected unexpectedly.")
            elif isinstance(e, httpx.ConnectError):
                logger.error("Could not connect to the server.")
            raise  # Re-raise the specific network error
        except Exception as e:
            # Catch any other unexpected errors
            logger.error(f"An unexpected error occurred while listing tools: {str(e)}", exc_info=True)
            raise

    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool on the MCP server."""
        if not self._client:
            raise ConnectionError("Client not connected")
        try:
            # Assuming the endpoint for calling a tool is /tools/{tool_name}
            response = await self._client.post(f"/tools/{tool_name}", json=args)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name}: {str(e)}")
            # Propagate the error for handling upstream
            raise

logger = logging.getLogger(__name__)


class MCPClient:
  """
  Client for interacting with MCP server and LLM services.
  """

  def __init__(self, mcp_server_url: str = "http://localhost:8000"):
    """
    Initialize MCP client with optional server URL.

    Args:
        mcp_server_url: URL of the MCP server to connect to
    """
    load_dotenv()  # Load environment variables
    self.mcp_server_url = mcp_server_url
    self.llm_provider = os.getenv("LLM_PROVIDER")
    self.llm_api_key = os.getenv("LLM_API_KEY")
    self.ollama_model = os.getenv("OLLAMA_MODEL", "deepseek-r1:7b")
    self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    self._validate_llm_config()

  def _validate_llm_config(self):
    """Validate LLM configuration from environment variables."""
    if not self.llm_provider:
      logger.warning("LLM_PROVIDER environment variable not set")
    if not self.llm_api_key:
      logger.warning("LLM_API_KEY environment variable not set")

  async def call_mcp_server(
    self, tool_name: str, args: Dict[str, Any]
  ) -> Dict[str, Any]:
    """
    Call an MCP server endpoint.

    Args:
        tool_name: Name of the MCP tool to call
        args: Arguments to pass to the tool

    Returns:
        Response from the MCP server
    """
    try:
      mcp_connection = await FastMCP.connect(self.mcp_server_url)
      async with mcp_connection as mcp:
        result = await mcp.call_tool(tool_name, args)
        return result
    except Exception as e:
      logger.error(f"Failed to call MCP tool {tool_name}: {str(e)}")
      return {"error": str(e)}

  async def call_llm(self, prompt: str) -> Optional[str]:
    """
    Call the configured LLM with a prompt.

    Args:
        prompt: The prompt to send to the LLM

    Returns:
        LLM response or None if not configured
    """
    if not self.llm_provider or not self.llm_api_key:
      logger.warning("LLM not properly configured, skipping call")
      return None

    if self.llm_provider.lower() == "ollama":
      try:
        import httpx
        async with httpx.AsyncClient() as client:
          response = await client.post(
            f"{self.ollama_base_url}/api/generate",
            json={
              "model": self.ollama_model,
              "prompt": prompt,
              "stream": False
            },
            timeout=30.0
          )
          response.raise_for_status()
          return response.json().get("response")
      except Exception as e:
        logger.error(f"Failed to call Ollama API: {str(e)}")
        return None
    
    # Fallback for other providers
    return f"LLM response to: {prompt}"

  async def call_uvx(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call a UVX tool through the MCP server.

    Args:
        tool_name: Name of the UVX tool to call
        args: Arguments to pass to the tool

    Returns:
        Response from the UVX tool
    """
    try:
      mcp_connection = await FastMCP.connect(self.mcp_server_url)
      async with mcp_connection as mcp:
        result = await mcp.call_tool(f"uvx_{tool_name}", args)
        return result
    except Exception as e:
      logger.error(f"Failed to call UVX tool {tool_name}: {str(e)}")
      return {"error": str(e)}

  async def process_natural_language(self, query: str) -> Dict[str, Any]:
    """
    Process natural language query and determine appropriate MCP tools to call.

    Args:
        query: Natural language query from user

    Returns:
        Dictionary containing tool selection and arguments in markdown format
    """
    if not self.llm_provider or not self.llm_api_key:
      logger.warning("LLM not configured, cannot process natural language query.")
      return {"error": "LLM not properly configured"}

    tools = None
    try:
        mcp_connection = await FastMCP.connect(self.mcp_server_url)
        async with mcp_connection as mcp:
            logger.info("Listing tools from MCP server...")
            tools = await mcp.list_tools()
            logger.info(f"Successfully listed {len(tools.get('tools', []))} tools.")
    except ConnectionError as e:
        logger.error(f"Connection error when listing tools: {str(e)}")
        return {"error": f"Failed to list tools: {str(e)}"}
    except httpx.RequestError as e:
         logger.error(f"Network error when listing tools: {str(e)}")
         return {"error": f"Failed to list tools: Network error - {str(e)}"}
    except httpx.HTTPStatusError as e:
         logger.error(f"HTTP error when listing tools: {e.response.status_code}")
         return {"error": f"Failed to list tools: Server error - {e.response.status_code}"}
    except Exception as e:
        logger.error(f"Unexpected error listing tools: {str(e)}", exc_info=True)
        # Use the error message from the exception if available, otherwise a generic message
        error_msg = str(e) if str(e) else "An unexpected error occurred."
        return {"error": f"Failed to list tools: {error_msg}"}

    if not tools or "error" in tools:
        logger.error(f"Failed to retrieve tools from MCP server. Response: {tools}")
        # Ensure a consistent error format is returned
        error_detail = tools.get("error", "Unknown error") if isinstance(tools, dict) else "Invalid response from server"
        return {"error": f"Failed to process natural language query: {error_detail}"}

    # Prepare prompt for LLM
    prompt = f"""Available MCP tools: {tools}
            
            User query: {query}
            
            Select the most appropriate tool(s) and provide arguments in JSON format.
            Return the response in markdown format with tool name and arguments."""

    # Call LLM to determine tool selection
    llm_response = await self.call_llm(prompt)

    # Format response as markdown
    markdown_response = f"""# MCP Tool Selection
            
            ## Query
            {query}
            
            ## Selected Tool
            {llm_response.get("tool", "No tool selected")}
            
            ## Arguments
            ```json
            {llm_response.get("args", {})}
            ```"""

    return {"markdown": markdown_response}

    
