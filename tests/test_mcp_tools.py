"""Unit tests for mcp_tools.py module.

This module contains tests for the MCP tools wrapper functions, focusing on
input validation and error handling.
"""

import pytest
from unittest.mock import patch

from devops_mcps import mcp_tools


class TestAzureTools:
  """Test cases for Azure tools validation."""

  @pytest.mark.asyncio
  async def test_list_azure_app_services_validation(self):
    """Test validation in list_azure_app_services."""
    # Test empty subscription_id
    result = await mcp_tools.list_azure_app_services(subscription_id="")
    assert "error" in result
    assert "Parameter 'subscription_id' cannot be empty" in result["error"]

  @pytest.mark.asyncio
  @patch("devops_mcps.azure.get_app_service_details")
  async def test_get_azure_app_service_details_validation(self, mock_get_details):
    """Test validation in get_azure_app_service_details."""
    # Test empty subscription_id
    result = await mcp_tools.get_azure_app_service_details(
      subscription_id="", resource_group="rg", app_name="app"
    )
    assert "error" in result
    assert "Parameter 'subscription_id' cannot be empty" in result["error"]

    # Test empty resource_group
    result = await mcp_tools.get_azure_app_service_details(
      subscription_id="sub", resource_group="", app_name="app"
    )
    assert "error" in result
    assert "Parameter 'resource_group' cannot be empty" in result["error"]

    # Test empty app_name
    result = await mcp_tools.get_azure_app_service_details(
      subscription_id="sub", resource_group="rg", app_name=""
    )
    assert "error" in result
    assert "Parameter 'app_name' cannot be empty" in result["error"]

  @pytest.mark.asyncio
  @patch("devops_mcps.azure.get_app_service_metrics")
  async def test_get_azure_app_service_metrics_validation(self, mock_get_metrics):
    """Test validation in get_azure_app_service_metrics."""
    # Test empty subscription_id
    result = await mcp_tools.get_azure_app_service_metrics(
      subscription_id="", resource_group="rg", app_name="app"
    )
    assert "error" in result
    assert "Parameter 'subscription_id' cannot be empty" in result["error"]

    # Test empty resource_group
    result = await mcp_tools.get_azure_app_service_metrics(
      subscription_id="sub", resource_group="", app_name="app"
    )
    assert "error" in result
    assert "Parameter 'resource_group' cannot be empty" in result["error"]

    # Test empty app_name
    result = await mcp_tools.get_azure_app_service_metrics(
      subscription_id="sub", resource_group="rg", app_name=""
    )
    assert "error" in result
    assert "Parameter 'app_name' cannot be empty" in result["error"]

  @pytest.mark.asyncio
  async def test_list_azure_app_service_plans_validation(self):
    """Test validation in list_azure_app_service_plans."""
    # Test empty subscription_id
    result = await mcp_tools.list_azure_app_service_plans(subscription_id="")
    assert "error" in result
    assert "Parameter 'subscription_id' cannot be empty" in result["error"]


class TestJenkinsTools:
  """Test cases for Jenkins tools validation."""

  @pytest.mark.asyncio
  async def test_get_jenkins_build_log_validation(self):
    """Test validation in get_jenkins_build_log."""
    # Test empty job_name
    result = await mcp_tools.get_jenkins_build_log(job_name="", build_number=1)
    assert "error" in result
    assert "Parameter 'job_name' cannot be empty" in result["error"]

    # Test None build_number
    result = await mcp_tools.get_jenkins_build_log(job_name="job", build_number=None)
    assert "error" in result
    assert "Parameter 'build_number' cannot be None" in result["error"]


class TestArtifactoryTools:
  """Test cases for Artifactory tools validation."""

  @pytest.mark.asyncio
  async def test_list_artifactory_items_validation(self):
    """Test validation in list_artifactory_items."""
    result = await mcp_tools.list_artifactory_items(repository="")
    assert "error" in result
    assert "Parameter 'repository' cannot be empty" in result["error"]

  @pytest.mark.asyncio
  async def test_search_artifactory_items_validation(self):
    """Test validation in search_artifactory_items."""
    result = await mcp_tools.search_artifactory_items(query="")
    assert "error" in result
    assert "Parameter 'query' cannot be empty" in result["error"]

  @pytest.mark.asyncio
  async def test_get_artifactory_item_info_validation(self):
    """Test validation in get_artifactory_item_info."""
    # Test empty repository
    result = await mcp_tools.get_artifactory_item_info(repository="", path="/path")
    assert "error" in result
    assert "Parameter 'repository' cannot be empty" in result["error"]

    # Test empty path
    result = await mcp_tools.get_artifactory_item_info(repository="repo", path="")
    assert "error" in result
    assert "Parameter 'path' cannot be empty" in result["error"]


class TestGitHubTools:
  """Test cases for GitHub tools validation."""

  @pytest.mark.asyncio
  async def test_search_repositories_validation(self):
    """Test validation in search_repositories."""
    result = await mcp_tools.search_repositories(query="")
    assert "error" in result
    assert "Parameter 'query' cannot be empty" in result["error"]

  @pytest.mark.asyncio
  async def test_get_file_contents_validation(self):
    """Test validation in get_file_contents."""
    # Test empty owner
    result = await mcp_tools.get_file_contents(owner="", repo="repo", path="path")
    assert "error" in result
    assert "Parameter 'owner' cannot be empty" in result["error"]

    # Test empty repo
    result = await mcp_tools.get_file_contents(owner="owner", repo="", path="path")
    assert "error" in result
    assert "Parameter 'repo' cannot be empty" in result["error"]

    # Test empty path
    result = await mcp_tools.get_file_contents(owner="owner", repo="repo", path="")
    assert "error" in result
    assert "Parameter 'path' cannot be empty" in result["error"]
