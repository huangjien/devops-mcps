import pytest
from unittest.mock import patch
from devops_mcps.client import MCPClient


@pytest.fixture
def client():
  return MCPClient("http://test-server")


@pytest.mark.asyncio
async def test_call_llm_not_configured(client):
  """Test LLM call when not configured."""
  client.llm_provider = None
  result = await client.call_llm("test prompt")
  assert result is None


@pytest.mark.asyncio
@patch("devops_mcps.client.MCPClient.call_llm")
async def test_process_natural_language(mock_call_llm, client):
  """Test natural language processing."""
  mock_call_llm.return_value = {"tool": "test", "args": {}}
  result = await client.process_natural_language("test query")
  assert "error" in result
  assert result["error"] == "LLM not properly configured"


@pytest.mark.asyncio
@patch("devops_mcps.client.MCPClient.call_llm")
async def test_process_natural_language_error(mock_call_llm, client):
  """Test natural language processing with LLM error."""
  mock_call_llm.side_effect = Exception("LLM error")
  result = await client.process_natural_language("test query")
  assert "error" in result
  assert result["error"] == "LLM not properly configured"


@pytest.mark.asyncio
@patch("devops_mcps.client.MCPClient.call_llm")
async def test_process_natural_language_invalid_response(mock_call_llm, client):
  """Test natural language processing with invalid LLM response."""
  mock_call_llm.return_value = "invalid response format"
  result = await client.process_natural_language("test query")
  assert "error" in result
  assert result["error"] == "LLM not properly configured"
