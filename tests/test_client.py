import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from devops_mcps.client import MCPClient

@pytest.fixture
def mcp_client():
    """Create a MCPClient instance with mocked FastMCP."""
    with patch('devops_mcps.client.FastMCP') as mock_fastmcp:
        client = MCPClient()
        # Configure the mock
        client.mcp = AsyncMock()
        yield client

def test_client_initialization():
    """Test MCPClient initialization with default and custom environment variables."""
    # Test with default values
    with patch.dict('os.environ', {}, clear=True):
        client = MCPClient()
        assert client.host == 'localhost'
        assert client.port == 8000

    # Test with custom environment variables
    with patch.dict('os.environ', {'MCP_HOST': 'testhost', 'MCP_PORT': '9000'}):
        client = MCPClient()
        assert client.host == 'testhost'
        assert client.port == 9000

@pytest.mark.asyncio
async def test_process_successful_dict_response(mcp_client):
    """Test processing a query that returns a dictionary response."""
    # Mock the list_tools response
    mock_tool = {'name': 'test_tool', 'description': 'test query'}
    mcp_client.mcp.list_tools.return_value = [mock_tool]
    
    # Mock the execute_tool response
    mock_result = {'key': 'value'}
    mcp_client.mcp.execute_tool.return_value = mock_result

    result = await mcp_client.process('test query')
    assert '## Results' in result
    assert '### key' in result
    assert 'value' in result

@pytest.mark.asyncio
async def test_process_successful_list_response(mcp_client):
    """Test processing a query that returns a list response."""
    # Mock the list_tools response
    mock_tool = {'name': 'test_tool', 'description': 'test query'}
    mcp_client.mcp.list_tools.return_value = [mock_tool]
    
    # Mock the execute_tool response
    mock_result = ['item1', 'item2']
    mcp_client.mcp.execute_tool.return_value = mock_result

    result = await mcp_client.process('test query')
    assert '## Results' in result
    assert '- item1' in result
    assert '- item2' in result

@pytest.mark.asyncio
async def test_process_no_suitable_tool(mcp_client):
    """Test processing a query when no suitable tool is found."""
    # Mock empty tools list
    mcp_client.mcp.list_tools.return_value = []

    result = await mcp_client.process('test query')
    assert 'No suitable tool found' in result

@pytest.mark.asyncio
async def test_process_error_handling(mcp_client):
    """Test error handling during query processing."""
    # Mock an error during tool execution
    mcp_client.mcp.list_tools.side_effect = Exception('Test error')

    with pytest.raises(RuntimeError) as exc_info:
        await mcp_client.process('test query')
    assert 'Failed to process query' in str(exc_info.value)

def test_format_dict_as_markdown(mcp_client):
    """Test dictionary to markdown formatting."""
    # Test normal dictionary
    test_dict = {'key1': 'value1', 'key2': 'value2'}
    result = mcp_client._format_dict_as_markdown(test_dict)
    assert '### key1' in result
    assert 'value1' in result
    assert '### key2' in result
    assert 'value2' in result

    # Test error dictionary
    error_dict = {'error': 'test error'}
    result = mcp_client._format_dict_as_markdown(error_dict)
    assert '## Error' in result
    assert 'test error' in result

def test_format_list_as_markdown(mcp_client):
    """Test list to markdown formatting."""
    # Test empty list
    result = mcp_client._format_list_as_markdown([])
    assert 'No results found' in result

    # Test list with mixed types
    test_list = ['item1', {'key': 'value'}, 'item2']
    result = mcp_client._format_list_as_markdown(test_list)
    assert '- item1' in result
    assert '### key' in result
    assert 'value' in result
    assert '- item2' in result