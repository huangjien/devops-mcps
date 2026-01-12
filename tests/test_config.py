"""Unit tests for config.py module.

This module contains comprehensive tests for configuration validation.
"""

import os
import unittest
from unittest.mock import patch

from devops_mcps.config import (
  validate_github_config,
  validate_jenkins_config,
  validate_artifactory_config,
  validate_azure_config,
  validate_server_config,
  validate_all_config,
  print_validation_report,
)


class TestGitHubConfigValidation(unittest.TestCase):
  """Test cases for GitHub configuration validation."""

  def setUp(self):
    """Set up test fixtures."""
    # Save original environment variables
    self.original_env = os.environ.copy()

  def tearDown(self):
    """Clean up after tests."""
    # Restore original environment variables
    os.environ.clear()
    os.environ.update(self.original_env)

  def test_valid_github_config(self):
    """Test validation with valid GitHub configuration."""
    os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = "ghp_test_token"
    is_valid, error = validate_github_config()
    self.assertTrue(is_valid)
    self.assertIsNone(error)

  def test_missing_github_token(self):
    """Test validation with missing GitHub token."""
    os.environ.pop("GITHUB_PERSONAL_ACCESS_TOKEN", None)
    is_valid, error = validate_github_config()
    self.assertFalse(is_valid)
    self.assertIsNotNone(error)
    self.assertIn("GITHUB_PERSONAL_ACCESS_TOKEN", error.get("error", ""))

  def test_invalid_github_api_url(self):
    """Test validation with invalid GitHub API URL."""
    os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = "ghp_test_token"
    os.environ["GITHUB_API_URL"] = "invalid_url"
    is_valid, error = validate_github_config()
    self.assertFalse(is_valid)
    self.assertIn("GITHUB_API_URL", error.get("error", ""))

  def test_valid_github_api_url(self):
    """Test validation with valid GitHub API URL."""
    os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = "ghp_test_token"
    os.environ["GITHUB_API_URL"] = "https://github.mycompany.com"
    is_valid, error = validate_github_config()
    self.assertTrue(is_valid)
    self.assertIsNone(error)


class TestJenkinsConfigValidation(unittest.TestCase):
  """Test cases for Jenkins configuration validation."""

  def setUp(self):
    """Set up test fixtures."""
    self.original_env = os.environ.copy()

  def tearDown(self):
    """Clean up after tests."""
    os.environ.clear()
    os.environ.update(self.original_env)

  def test_valid_jenkins_config(self):
    """Test validation with valid Jenkins configuration."""
    os.environ["JENKINS_URL"] = "https://jenkins.example.com"
    os.environ["JENKINS_USER"] = "test_user"
    os.environ["JENKINS_TOKEN"] = "test_token"
    is_valid, error = validate_jenkins_config()
    self.assertTrue(is_valid)
    self.assertIsNone(error)

  def test_missing_jenkins_url(self):
    """Test validation with missing Jenkins URL."""
    os.environ.pop("JENKINS_URL", None)
    os.environ["JENKINS_USER"] = "test_user"
    os.environ["JENKINS_TOKEN"] = "test_token"
    is_valid, error = validate_jenkins_config()
    self.assertFalse(is_valid)
    self.assertIn("JENKINS_URL", error.get("error", ""))

  def test_missing_jenkins_user(self):
    """Test validation with missing Jenkins user."""
    os.environ.pop("JENKINS_USER", None)
    os.environ["JENKINS_URL"] = "https://jenkins.example.com"
    os.environ["JENKINS_TOKEN"] = "test_token"
    is_valid, error = validate_jenkins_config()
    self.assertFalse(is_valid)
    self.assertIn("JENKINS_USER", error.get("error", ""))

  def test_missing_jenkins_token(self):
    """Test validation with missing Jenkins token."""
    os.environ.pop("JENKINS_TOKEN", None)
    os.environ["JENKINS_URL"] = "https://jenkins.example.com"
    os.environ["JENKINS_USER"] = "test_user"
    is_valid, error = validate_jenkins_config()
    self.assertFalse(is_valid)
    self.assertIn("JENKINS_TOKEN", error.get("error", ""))

  def test_invalid_jenkins_url(self):
    """Test validation with invalid Jenkins URL."""
    os.environ["JENKINS_URL"] = "invalid_url"
    os.environ["JENKINS_USER"] = "test_user"
    os.environ["JENKINS_TOKEN"] = "test_token"
    is_valid, error = validate_jenkins_config()
    self.assertFalse(is_valid)
    self.assertIn("JENKINS_URL", error.get("error", ""))

  def test_valid_log_length(self):
    """Test validation with valid LOG_LENGTH."""
    os.environ["JENKINS_URL"] = "https://jenkins.example.com"
    os.environ["JENKINS_USER"] = "test_user"
    os.environ["JENKINS_TOKEN"] = "test_token"
    os.environ["LOG_LENGTH"] = "10240"
    is_valid, error = validate_jenkins_config()
    self.assertTrue(is_valid)
    self.assertIsNone(error)

  def test_invalid_log_length_negative(self):
    """Test validation with negative LOG_LENGTH."""
    os.environ["JENKINS_URL"] = "https://jenkins.example.com"
    os.environ["JENKINS_USER"] = "test_user"
    os.environ["JENKINS_TOKEN"] = "test_token"
    os.environ["LOG_LENGTH"] = "-100"
    is_valid, error = validate_jenkins_config()
    self.assertFalse(is_valid)
    self.assertIn("LOG_LENGTH", error.get("error", ""))

  def test_invalid_log_length_non_numeric(self):
    """Test validation with non-numeric LOG_LENGTH."""
    os.environ["JENKINS_URL"] = "https://jenkins.example.com"
    os.environ["JENKINS_USER"] = "test_user"
    os.environ["JENKINS_TOKEN"] = "test_token"
    os.environ["LOG_LENGTH"] = "invalid"
    is_valid, error = validate_jenkins_config()
    self.assertFalse(is_valid)
    self.assertIn("LOG_LENGTH", error.get("error", ""))

  def test_no_jenkins_config(self):
    """Test validation when no Jenkins config is provided (optional)."""
    is_valid, error = validate_jenkins_config()
    self.assertTrue(is_valid)
    self.assertIsNone(error)


class TestArtifactoryConfigValidation(unittest.TestCase):
  """Test cases for Artifactory configuration validation."""

  def setUp(self):
    """Set up test fixtures."""
    self.original_env = os.environ.copy()

  def tearDown(self):
    """Clean up after tests."""
    os.environ.clear()
    os.environ.update(self.original_env)

  def test_valid_artifactory_config_with_token(self):
    """Test validation with valid Artifactory config (identity token)."""
    os.environ["ARTIFACTORY_URL"] = "https://artifactory.example.com"
    os.environ["ARTIFACTORY_IDENTITY_TOKEN"] = "test_token"
    is_valid, error = validate_artifactory_config()
    self.assertTrue(is_valid)
    self.assertIsNone(error)

  def test_valid_artifactory_config_with_credentials(self):
    """Test validation with valid Artifactory config (username/password)."""
    os.environ["ARTIFACTORY_URL"] = "https://artifactory.example.com"
    os.environ["ARTIFACTORY_USERNAME"] = "test_user"
    os.environ["ARTIFACTORY_PASSWORD"] = "test_password"
    is_valid, error = validate_artifactory_config()
    self.assertTrue(is_valid)
    self.assertIsNone(error)

  def test_missing_artifactory_url(self):
    """Test validation with missing Artifactory URL."""
    os.environ.pop("ARTIFACTORY_URL", None)
    os.environ["ARTIFACTORY_IDENTITY_TOKEN"] = "test_token"
    is_valid, error = validate_artifactory_config()
    self.assertFalse(is_valid)
    self.assertIn("ARTIFACTORY_URL", error.get("error", ""))

  def test_missing_artifactory_auth(self):
    """Test validation with missing Artifactory authentication."""
    os.environ.pop("ARTIFACTORY_IDENTITY_TOKEN", None)
    os.environ.pop("ARTIFACTORY_USERNAME", None)
    os.environ.pop("ARTIFACTORY_PASSWORD", None)
    os.environ["ARTIFACTORY_URL"] = "https://artifactory.example.com"
    is_valid, error = validate_artifactory_config()
    self.assertFalse(is_valid)
    self.assertIn("ARTIFACTORY_AUTHENTICATION", error.get("error", ""))

  def test_invalid_artifactory_url(self):
    """Test validation with invalid Artifactory URL."""
    os.environ["ARTIFACTORY_URL"] = "invalid_url"
    os.environ["ARTIFACTORY_IDENTITY_TOKEN"] = "test_token"
    is_valid, error = validate_artifactory_config()
    self.assertFalse(is_valid)
    self.assertIn("ARTIFACTORY_URL", error.get("error", ""))

  def test_no_artifactory_config(self):
    """Test validation when no Artifactory config is provided (optional)."""
    is_valid, error = validate_artifactory_config()
    self.assertTrue(is_valid)
    self.assertIsNone(error)


class TestAzureConfigValidation(unittest.TestCase):
  """Test cases for Azure configuration validation."""

  def setUp(self):
    """Set up test fixtures."""
    self.original_env = os.environ.copy()

  def tearDown(self):
    """Clean up after tests."""
    os.environ.clear()
    os.environ.update(self.original_env)

  def test_valid_azure_config(self):
    """Test validation with valid Azure configuration."""
    os.environ["AZURE_CLIENT_ID"] = "test_client_id"
    os.environ["AZURE_CLIENT_SECRET"] = "test_secret"
    os.environ["AZURE_TENANT_ID"] = "test_tenant"
    is_valid, error = validate_azure_config()
    self.assertTrue(is_valid)
    self.assertIsNone(error)

  def test_partial_azure_config(self):
    """Test validation with partial Azure configuration."""
    os.environ["AZURE_CLIENT_ID"] = "test_client_id"
    is_valid, error = validate_azure_config()
    self.assertFalse(is_valid)
    self.assertIn("AZURE_CREDENTIALS", error.get("error", ""))

  def test_no_azure_config(self):
    """Test validation when no Azure config is provided (optional)."""
    is_valid, error = validate_azure_config()
    self.assertTrue(is_valid)
    self.assertIsNone(error)


class TestServerConfigValidation(unittest.TestCase):
  """Test cases for server configuration validation."""

  def setUp(self):
    """Set up test fixtures."""
    self.original_env = os.environ.copy()

  def tearDown(self):
    """Clean up after tests."""
    os.environ.clear()
    os.environ.update(self.original_env)

  def test_valid_server_config(self):
    """Test validation with valid server configuration."""
    is_valid, error = validate_server_config()
    self.assertTrue(is_valid)
    self.assertIsNone(error)

  def test_invalid_mcp_port_low(self):
    """Test validation with MCP port too low."""
    os.environ["MCP_PORT"] = "0"
    is_valid, error = validate_server_config()
    self.assertFalse(is_valid)
    self.assertIn("MCP_PORT", error.get("error", ""))

  def test_invalid_mcp_port_high(self):
    """Test validation with MCP port too high."""
    os.environ["MCP_PORT"] = "70000"
    is_valid, error = validate_server_config()
    self.assertFalse(is_valid)
    self.assertIn("MCP_PORT", error.get("error", ""))

  def test_invalid_mcp_port_non_numeric(self):
    """Test validation with non-numeric MCP port."""
    os.environ["MCP_PORT"] = "invalid"
    is_valid, error = validate_server_config()
    self.assertFalse(is_valid)
    self.assertIn("MCP_PORT", error.get("error", ""))

  def test_valid_mcp_port(self):
    """Test validation with valid MCP port."""
    os.environ["MCP_PORT"] = "8080"
    is_valid, error = validate_server_config()
    self.assertTrue(is_valid)
    self.assertIsNone(error)

  def test_invalid_log_level(self):
    """Test validation with invalid log level."""
    os.environ["LOG_LEVEL"] = "INVALID"
    is_valid, error = validate_server_config()
    self.assertFalse(is_valid)
    self.assertIn("LOG_LEVEL", error.get("error", ""))

  def test_valid_log_levels(self):
    """Test validation with valid log levels."""
    for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
      os.environ["LOG_LEVEL"] = level
      is_valid, error = validate_server_config()
      self.assertTrue(is_valid, f"Failed for log level: {level}")
      self.assertIsNone(error, f"Failed for log level: {level}")


class TestValidateAllConfig(unittest.TestCase):
  """Test cases for validate_all_config function."""

  def setUp(self):
    """Set up test fixtures."""
    self.original_env = os.environ.copy()

  def tearDown(self):
    """Clean up after tests."""
    os.environ.clear()
    os.environ.update(self.original_env)

  def test_all_valid_config(self):
    """Test validation with all valid configuration."""
    os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = "ghp_test_token"
    is_valid, errors = validate_all_config()
    self.assertTrue(is_valid)
    self.assertEqual(len(errors), 0)

  def test_invalid_config_non_strict(self):
    """Test validation with errors in non-strict mode."""
    os.environ.pop("GITHUB_PERSONAL_ACCESS_TOKEN", None)
    is_valid, errors = validate_all_config(strict=False)
    self.assertFalse(is_valid)
    self.assertGreater(len(errors), 0)

  def test_invalid_config_strict(self):
    """Test validation with errors in strict mode."""
    os.environ.pop("GITHUB_PERSONAL_ACCESS_TOKEN", None)
    is_valid, errors = validate_all_config(strict=True)
    self.assertFalse(is_valid)
    self.assertGreater(len(errors), 0)


class TestPrintValidationReport(unittest.TestCase):
  """Test cases for print_validation_report function."""

  @patch("devops_mcps.config.logger")
  def test_print_errors(self, mock_logger):
    """Test printing error messages."""
    errors = ["Error 1", "Error 2"]
    print_validation_report(errors)
    mock_logger.error.assert_called()
    error_calls = [call[0][0] for call in mock_logger.error.call_args_list]
    self.assertTrue(
      any("Configuration validation failed" in str(call) for call in error_calls)
    )

  @patch("devops_mcps.config.logger")
  def test_print_warnings(self, mock_logger):
    """Test printing warning messages."""
    warnings = ["Warning 1", "Warning 2"]
    print_validation_report([], warnings)
    mock_logger.warning.assert_called()
    self.assertEqual(mock_logger.warning.call_count, 2)

  @patch("devops_mcps.config.logger")
  def test_print_success(self, mock_logger):
    """Test printing success message."""
    print_validation_report([], [])
    mock_logger.info.assert_called_with("Configuration validation passed.")


if __name__ == "__main__":
  unittest.main()
