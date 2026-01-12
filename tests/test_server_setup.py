"""Unit tests for server_setup.py module.

This module contains tests for server setup, version retrieval, and client initialization.
"""

import unittest
from unittest.mock import patch, MagicMock
from importlib.metadata import PackageNotFoundError

from devops_mcps import server_setup


class TestServerSetup(unittest.TestCase):
  """Test cases for server_setup module."""

  @patch("devops_mcps.server_setup.version")
  def test_get_package_version_success(self, mock_version):
    """Test successful package version retrieval."""
    mock_version.return_value = "1.0.0"
    version = server_setup.get_package_version()
    self.assertEqual(version, "1.0.0")

  @patch("devops_mcps.server_setup.version")
  def test_get_package_version_not_found(self, mock_version):
    """Test package version retrieval when package is not found."""
    mock_version.side_effect = PackageNotFoundError
    version = server_setup.get_package_version()
    self.assertEqual(version, "?.?.?")

  @patch("devops_mcps.server_setup.get_package_version")
  @patch("devops_mcps.server_setup.FastMCP")
  def test_create_mcp_server(self, mock_fastmcp, mock_get_version):
    """Test creation of FastMCP server."""
    mock_get_version.return_value = "1.0.0"
    server = server_setup.create_mcp_server()
    mock_fastmcp.assert_called_with("DevOps MCP Server v1.0.0 (Github & Jenkins)")
    self.assertIsNotNone(server)

  @patch("devops_mcps.jenkins.j", create=True)
  @patch("devops_mcps.jenkins.JENKINS_URL", "url", create=True)
  @patch("devops_mcps.jenkins.JENKINS_USER", "user", create=True)
  @patch("devops_mcps.jenkins.JENKINS_TOKEN", "token", create=True)
  @patch("devops_mcps.utils.github.github_client")
  @patch("devops_mcps.github.initialize_github_client")
  @patch("sys.exit")
  @patch("os.environ.get")
  def test_initialize_clients_github_failure_with_token(
    self, mock_env_get, mock_exit, mock_init_gh, mock_github_client, mock_jenkins_j
  ):
    """Test initialization failure when GitHub token is present but client is None."""
    mock_github_client.g = None
    mock_env_get.return_value = "fake_token"  # GITHUB_PERSONAL_ACCESS_TOKEN present

    server_setup.initialize_clients()

    mock_exit.assert_called_with(1)

  @patch("devops_mcps.jenkins.j", create=True)
  @patch("devops_mcps.jenkins.JENKINS_URL", "url", create=True)
  @patch("devops_mcps.utils.github.github_client")
  @patch("devops_mcps.github.initialize_github_client")
  @patch("sys.exit")
  def test_initialize_clients_github_warning(
    self, mock_exit, mock_init_gh, mock_github_client, mock_jenkins_j
  ):
    """Test initialization warning when GitHub token is missing."""
    mock_github_client.g = None
    # Mock Jenkins success to isolate GitHub test
    mock_jenkins_j.return_value = MagicMock()

    with patch("os.environ.get", return_value=None):
      server_setup.initialize_clients()
      mock_exit.assert_not_called()

  @patch("devops_mcps.jenkins.j", None, create=True)
  @patch("devops_mcps.jenkins.JENKINS_URL", "url", create=True)
  @patch("devops_mcps.jenkins.JENKINS_USER", "user", create=True)
  @patch("devops_mcps.jenkins.JENKINS_TOKEN", "token", create=True)
  @patch("devops_mcps.utils.github.github_client")
  @patch("devops_mcps.github.initialize_github_client")
  @patch("sys.exit")
  def test_initialize_clients_jenkins_failure_with_credentials(
    self, mock_exit, mock_init_gh, mock_github_client
  ):
    """Test initialization failure when Jenkins credentials are present but client is None."""
    # Mock GitHub success
    mock_github_client.g = MagicMock()

    server_setup.initialize_clients()

    mock_exit.assert_called_with(1)

  @patch("devops_mcps.jenkins.j", None, create=True)
  @patch("devops_mcps.jenkins.JENKINS_URL", None, create=True)
  @patch("devops_mcps.utils.github.github_client")
  @patch("devops_mcps.github.initialize_github_client")
  @patch("sys.exit")
  def test_initialize_clients_jenkins_warning(
    self, mock_exit, mock_init_gh, mock_github_client
  ):
    """Test initialization warning when Jenkins credentials are missing."""
    # Mock GitHub success
    mock_github_client.g = MagicMock()

    server_setup.initialize_clients()

    mock_exit.assert_not_called()


if __name__ == "__main__":
  unittest.main()
