"""Unit tests for health.py module.

This module contains comprehensive tests for health check functionality.
"""

import os
import unittest
from unittest.mock import patch, MagicMock

from devops_mcps.health import (
  check_github_health,
  check_jenkins_health,
  check_azure_health,
  check_artifactory_health,
  check_cache_health,
  get_overall_health,
  health_check_response,
)


class TestGitHubHealthCheck(unittest.TestCase):
  """Test cases for GitHub health check."""

  def setUp(self):
    """Set up test fixtures."""
    self.original_env = os.environ.copy()

  def tearDown(self):
    """Clean up after tests."""
    os.environ.clear()
    os.environ.update(self.original_env)

  @patch("devops_mcps.health.github.gh_get_current_user_info")
  def test_github_healthy(self, mock_get_user):
    """Test GitHub health check when healthy."""
    mock_get_user.return_value = {"login": "test_user"}
    os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = "test_token"

    status = check_github_health()

    self.assertEqual(status["status"], "healthy")
    self.assertEqual(status["authenticated"], True)
    self.assertIn("test_user", status["message"])

  @patch("devops_mcps.health.github.gh_get_current_user_info")
  def test_github_degraded(self, mock_get_user):
    """Test GitHub health check when degraded."""
    mock_get_user.return_value = {}
    os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = "test_token"

    status = check_github_health()

    self.assertEqual(status["status"], "degraded")
    self.assertEqual(status["authenticated"], False)

  @patch(
    "devops_mcps.health.github.gh_get_current_user_info",
    side_effect=Exception("API Error"),
  )
  def test_github_unhealthy(self, mock_get_user):
    """Test GitHub health check when unhealthy."""
    os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = "test_token"

    status = check_github_health()

    self.assertEqual(status["status"], "unhealthy")
    self.assertEqual(status["authenticated"], False)
    self.assertIn("API Error", status["message"])

  def test_github_not_configured(self):
    """Test GitHub health check when not configured."""
    os.environ.pop("GITHUB_PERSONAL_ACCESS_TOKEN", None)

    status = check_github_health()

    self.assertEqual(status["status"], "not_configured")
    self.assertEqual(status["authenticated"], False)


class TestJenkinsHealthCheck(unittest.TestCase):
  """Test cases for Jenkins health check."""

  def setUp(self):
    """Set up test fixtures."""
    self.original_env = os.environ.copy()

  def tearDown(self):
    """Clean up after tests."""
    os.environ.clear()
    os.environ.update(self.original_env)

  @patch("devops_mcps.health.jenkins.j.get_master_data")
  def test_jenkins_healthy(self, mock_get_master):
    """Test Jenkins health check when healthy."""
    mock_get_master.return_value = {}
    os.environ["JENKINS_URL"] = "https://jenkins.test.com"
    os.environ["JENKINS_USER"] = "test_user"
    os.environ["JENKINS_TOKEN"] = "test_token"

    status = check_jenkins_health()

    self.assertEqual(status["status"], "healthy")
    self.assertEqual(status["authenticated"], True)

  @patch(
    "devops_mcps.health.jenkins.j.get_master_data",
    side_effect=Exception("Connection Error"),
  )
  def test_jenkins_unhealthy(self, mock_get_master):
    """Test Jenkins health check when unhealthy."""
    os.environ["JENKINS_URL"] = "https://jenkins.test.com"
    os.environ["JENKINS_USER"] = "test_user"
    os.environ["JENKINS_TOKEN"] = "test_token"

    status = check_jenkins_health()

    self.assertEqual(status["status"], "unhealthy")
    self.assertEqual(status["authenticated"], False)
    self.assertIn("Connection Error", status["message"])

  def test_jenkins_not_configured(self):
    """Test Jenkins health check when not configured."""
    os.environ.pop("JENKINS_URL", None)

    status = check_jenkins_health()

    self.assertEqual(status["status"], "not_configured")
    self.assertEqual(status["authenticated"], False)


class TestAzureHealthCheck(unittest.TestCase):
  """Test cases for Azure health check."""

  def setUp(self):
    """Set up test fixtures."""
    self.original_env = os.environ.copy()

  def tearDown(self):
    """Clean up after tests."""
    os.environ.clear()
    os.environ.update(self.original_env)

  @patch("devops_mcps.health.azure.get_subscriptions")
  @patch("devops_mcps.health.azure_auth.get_azure_credential")
  def test_azure_healthy(self, mock_get_credential, mock_get_subs):
    """Test Azure health check when healthy."""
    mock_get_credential.return_value = "test_credential"
    mock_get_subs.return_value = [{"id": "sub1"}]
    os.environ["AZURE_CLIENT_ID"] = "test_client_id"

    status = check_azure_health()

    self.assertEqual(status["status"], "healthy")
    self.assertEqual(status["authenticated"], True)

  @patch("devops_mcps.health.azure.get_subscriptions")
  @patch("devops_mcps.health.azure_auth.get_azure_credential")
  def test_azure_degraded(self, mock_get_credential, mock_get_subs):
    """Test Azure health check when degraded."""
    mock_get_credential.return_value = "test_credential"
    mock_get_subs.return_value = []
    os.environ["AZURE_CLIENT_ID"] = "test_client_id"

    status = check_azure_health()

    self.assertEqual(status["status"], "degraded")
    self.assertEqual(status["authenticated"], True)

  @patch(
    "devops_mcps.health.azure_auth.get_azure_credential",
    side_effect=Exception("Auth Error"),
  )
  def test_azure_unhealthy(self, mock_get_credential):
    """Test Azure health check when unhealthy."""
    os.environ["AZURE_CLIENT_ID"] = "test_client_id"

    status = check_azure_health()

    self.assertEqual(status["status"], "unhealthy")
    self.assertEqual(status["authenticated"], False)
    self.assertIn("Auth Error", status["message"])

  def test_azure_not_configured(self):
    """Test Azure health check when not configured."""
    os.environ.pop("AZURE_CLIENT_ID", None)

    status = check_azure_health()

    self.assertEqual(status["status"], "not_configured")
    self.assertEqual(status["authenticated"], False)


class TestArtifactoryHealthCheck(unittest.TestCase):
  """Test cases for Artifactory health check."""

  def setUp(self):
    """Set up test fixtures."""
    self.original_env = os.environ.copy()

  def tearDown(self):
    """Clean up after tests."""
    os.environ.clear()
    os.environ.update(self.original_env)

  @patch("devops_mcps.health.artifactory_auth.get_auth")
  def test_artifactory_healthy(self, mock_get_auth):
    """Test Artifactory health check when healthy."""
    mock_get_auth.return_value = "test_auth"
    os.environ["ARTIFACTORY_URL"] = "https://artifactory.test.com"

    status = check_artifactory_health()

    self.assertEqual(status["status"], "healthy")
    self.assertEqual(status["authenticated"], True)

  @patch("devops_mcps.health.artifactory_auth.get_auth", return_value=None)
  def test_artifactory_degraded(self, mock_get_auth):
    """Test Artifactory health check when degraded."""
    os.environ["ARTIFACTORY_URL"] = "https://artifactory.test.com"

    status = check_artifactory_health()

    self.assertEqual(status["status"], "degraded")
    self.assertEqual(status["authenticated"], False)

  @patch(
    "devops_mcps.health.artifactory_auth.get_auth",
    side_effect=Exception("Connection Error"),
  )
  def test_artifactory_unhealthy(self, mock_get_auth):
    """Test Artifactory health check when unhealthy."""
    os.environ["ARTIFACTORY_URL"] = "https://artifactory.test.com"

    status = check_artifactory_health()

    self.assertEqual(status["status"], "unhealthy")
    self.assertEqual(status["authenticated"], False)
    self.assertIn("Connection Error", status["message"])

  def test_artifactory_not_configured(self):
    """Test Artifactory health check when not configured."""
    os.environ.pop("ARTIFACTORY_URL", None)

    status = check_artifactory_health()

    self.assertEqual(status["status"], "not_configured")
    self.assertEqual(status["authenticated"], False)


class TestCacheHealthCheck(unittest.TestCase):
  """Test cases for cache health check."""

  def setUp(self):
    """Set up test fixtures."""
    self.original_env = os.environ.copy()

  def tearDown(self):
    """Clean up after tests."""
    os.environ.clear()
    os.environ.update(self.original_env)

  @patch("devops_mcps.health.cache.CacheManager")
  def test_cache_healthy(self, mock_cache_class):
    """Test cache health check when healthy."""
    mock_instance = MagicMock()
    mock_instance.get.return_value = "ok"
    mock_instance.set.return_value = None
    mock_cache_class.return_value = mock_instance

    status = check_cache_health()

    self.assertEqual(status["status"], "healthy")

  @patch("devops_mcps.health.cache.CacheManager")
  def test_cache_unhealthy(self, mock_cache_class):
    """Test cache health check when unhealthy."""
    mock_instance = MagicMock()
    mock_instance.get.return_value = "unexpected"
    mock_instance.set.side_effect = Exception("Cache Error")
    mock_cache_class.return_value = mock_instance

    status = check_cache_health()

    self.assertEqual(status["status"], "unhealthy")
    self.assertIn("Cache Error", status["message"])


class TestOverallHealthCheck(unittest.TestCase):
  """Test cases for overall health check."""

  def setUp(self):
    """Set up test fixtures."""
    self.original_env = os.environ.copy()

  def tearDown(self):
    """Clean up after tests."""
    os.environ.clear()
    os.environ.update(self.original_env)

  @patch("devops_mcps.health.check_github_health")
  @patch("devops_mcps.health.check_jenkins_health")
  @patch("devops_mcps.health.check_azure_health")
  @patch("devops_mcps.health.check_artifactory_health")
  @patch("devops_mcps.health.check_cache_health")
  def test_all_healthy(
    self, mock_github, mock_jenkins, mock_azure, mock_artifactory, mock_cache
  ):
    """Test overall health check when all services are healthy."""
    mock_github.return_value = {"status": "healthy", "authenticated": True}
    mock_jenkins.return_value = {"status": "healthy", "authenticated": True}
    mock_azure.return_value = {"status": "healthy", "authenticated": True}
    mock_artifactory.return_value = {"status": "healthy", "authenticated": True}
    mock_cache.return_value = {"status": "healthy"}

    status = get_overall_health()

    self.assertEqual(status["status"], "healthy")
    self.assertEqual(status["healthy_count"], 5)
    self.assertEqual(status["total_count"], 5)

  @patch("devops_mcps.health.check_github_health")
  @patch("devops_mcps.health.check_jenkins_health")
  @patch("devops_mcps.health.check_azure_health")
  @patch("devops_mcps.health.check_artifactory_health")
  @patch("devops_mcps.health.check_cache_health")
  def test_mixed_health(
    self, mock_github, mock_jenkins, mock_azure, mock_artifactory, mock_cache
  ):
    """Test overall health check with mixed statuses."""
    mock_github.return_value = {"status": "healthy", "authenticated": True}
    mock_jenkins.return_value = {"status": "degraded", "authenticated": False}
    mock_azure.return_value = {"status": "healthy", "authenticated": True}
    mock_artifactory.return_value = {"status": "healthy", "authenticated": True}
    mock_cache.return_value = {"status": "healthy"}

    status = get_overall_health()

    self.assertEqual(status["status"], "degraded")
    self.assertEqual(status["healthy_count"], 4)
    self.assertEqual(status["total_count"], 5)

  @patch("devops_mcps.health.check_github_health")
  @patch("devops_mcps.health.check_jenkins_health")
  @patch("devops_mcps.health.check_azure_health")
  @patch("devops_mcps.health.check_artifactory_health")
  @patch("devops_mcps.health.check_cache_health")
  def test_all_unhealthy(
    self, mock_github, mock_jenkins, mock_azure, mock_artifactory, mock_cache
  ):
    """Test overall health check when all services are unhealthy."""
    mock_github.return_value = {"status": "unhealthy", "authenticated": False}
    mock_jenkins.return_value = {"status": "unhealthy", "authenticated": False}
    mock_azure.return_value = {"status": "unhealthy", "authenticated": False}
    mock_artifactory.return_value = {"status": "unhealthy", "authenticated": False}
    mock_cache.return_value = {"status": "unhealthy"}

    status = get_overall_health()

    self.assertEqual(status["status"], "unhealthy")
    self.assertEqual(status["healthy_count"], 0)
    self.assertEqual(status["total_count"], 5)


class TestHealthCheckResponse(unittest.TestCase):
  """Test cases for health check response generation."""

  @patch("devops_mcps.health.get_overall_health")
  def test_health_check_response(self, mock_get_health):
    """Test health check response generation."""
    mock_get_health.return_value = {
      "status": "healthy",
      "message": "All services are healthy",
      "services": {
        "github": {"status": "healthy"},
        "jenkins": {"status": "healthy"},
      },
      "healthy_count": 2,
      "total_count": 2,
    }

    response = health_check_response()

    self.assertIn("status", response)
    self.assertIn("services", response)
    self.assertIn("healthy_count", response)
    self.assertIn("total_count", response)


if __name__ == "__main__":
  unittest.main()
