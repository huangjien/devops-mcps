"""Health check module for DevOps MCP Server.

This module provides health check functionality for monitoring server status
and checking connectivity to external services.
"""

import logging
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Import modules at module level for test patching
from . import github, jenkins, azure  # noqa: E402
from .utils.github import github_client  # noqa: E402
from .utils.azure import azure_auth  # noqa: E402
from .utils.artifactory import artifactory_auth  # noqa: E402
from .cache import cache  # noqa: E402


def check_github_health() -> Dict[str, Any]:
  """Check GitHub client health.

  Returns:
      Dict with health status information
  """
  status = {
    "service": "github",
    "status": "unknown",
    "message": "",
  }

  if github_client.g is not None:
    try:
      # Test connection by getting current user
      user = github.gh_get_current_user_info()
      if user and "login" in user:
        status["status"] = "healthy"
        status["message"] = f"Connected as {user.get('login', 'unknown')}"
        status["authenticated"] = True
      else:
        status["status"] = "degraded"
        status["message"] = "Connected but could not authenticate"
        status["authenticated"] = False
    except Exception as e:
      status["status"] = "unhealthy"
      status["message"] = f"Connection error: {str(e)}"
      status["authenticated"] = False
  else:
    status["status"] = "not_configured"
    status["message"] = "GitHub client not initialized"
    status["authenticated"] = False

  return status


def check_jenkins_health() -> Dict[str, Any]:
  """Check Jenkins client health.

  Returns:
      Dict with health status information
  """
  status = {
    "service": "jenkins",
    "status": "unknown",
    "message": "",
  }

  if jenkins.j is not None:
    try:
      # Test connection by getting master data
      _ = jenkins.j.get_master_data()
      status["status"] = "healthy"
      status["message"] = "Connected to Jenkins server"
      status["authenticated"] = True
    except Exception as e:
      status["status"] = "unhealthy"
      status["message"] = f"Connection error: {str(e)}"
      status["authenticated"] = False
  else:
    status["status"] = "not_configured"
    status["message"] = "Jenkins client not initialized"
    status["authenticated"] = False

  return status


def check_azure_health() -> Dict[str, Any]:
  """Check Azure client health.

  Returns:
      Dict with health status information
  """
  status = {
    "service": "azure",
    "status": "unknown",
    "message": "",
  }

  # Check if Azure is configured by checking for required environment variables
  if not os.environ.get("AZURE_CLIENT_ID"):
    status["status"] = "not_configured"
    status["message"] = "Azure credentials not configured"
    status["authenticated"] = False
    return status

  try:
    # Test connection by getting subscriptions
    credential = azure_auth.get_azure_credential()
    if credential:
      subscriptions = azure.get_subscriptions()
      if subscriptions:
        status["status"] = "healthy"
        status["message"] = f"Connected to Azure ({len(subscriptions)} subscriptions)"
        status["authenticated"] = True
      else:
        status["status"] = "degraded"
        status["message"] = "Connected but no subscriptions found"
        status["authenticated"] = True
    else:
      status["status"] = "not_configured"
      status["message"] = "Azure credentials not configured"
      status["authenticated"] = False
  except Exception as e:
    status["status"] = "unhealthy"
    status["message"] = f"Connection error: {str(e)}"
    status["authenticated"] = False

  return status


def check_artifactory_health() -> Dict[str, Any]:
  """Check Artifactory client health.

  Returns:
      Dict with health status information
  """
  status = {
    "service": "artifactory",
    "status": "unknown",
    "message": "",
  }

  url = os.environ.get("ARTIFACTORY_URL")
  if url:
    try:
      # Test connection by getting auth
      auth = artifactory_auth.get_auth()
      if auth:
        status["status"] = "healthy"
        status["message"] = f"Connected to Artifactory at {url}"
        status["authenticated"] = True
      else:
        status["status"] = "degraded"
        status["message"] = "Artifactory URL configured but authentication failed"
        status["authenticated"] = False
    except Exception as e:
      status["status"] = "unhealthy"
      status["message"] = f"Connection error: {str(e)}"
      status["authenticated"] = False
  else:
    status["status"] = "not_configured"
    status["message"] = "Artifactory URL not configured"
    status["authenticated"] = False

  return status


def check_cache_health() -> Dict[str, Any]:
  """Check cache health.

  Returns:
      Dict with health status information
  """
  status = {
    "service": "cache",
    "status": "unknown",
    "message": "",
  }

  try:
    # Test cache by setting and getting a value
    cache.set("_health_check", "ok", ttl=10)
    value = cache.get("_health_check")
    if value == "ok":
      status["status"] = "healthy"
      status["message"] = "Cache is operational"
    else:
      status["status"] = "unhealthy"
      status["message"] = "Cache returned unexpected value"
  except Exception as e:
    status["status"] = "unhealthy"
    status["message"] = f"Cache error: {str(e)}"

  return status


def get_overall_health() -> Dict[str, Any]:
  """Get overall health status of all services.

  Returns:
      Dict with overall health status and individual service statuses
  """
  services = {
    "github": check_github_health(),
    "jenkins": check_jenkins_health(),
    "azure": check_azure_health(),
    "artifactory": check_artifactory_health(),
    "cache": check_cache_health(),
  }

  # Determine overall status
  healthy_count = sum(1 for s in services.values() if s.get("status") == "healthy")
  total_count = len(services)

  if healthy_count == total_count:
    overall_status = "healthy"
    overall_message = "All services are healthy"
  elif healthy_count > 0:
    overall_status = "degraded"
    overall_message = f"{healthy_count}/{total_count} services are healthy"
  else:
    overall_status = "unhealthy"
    overall_message = "No services are healthy"

  return {
    "status": overall_status,
    "message": overall_message,
    "services": services,
    "healthy_count": healthy_count,
    "total_count": total_count,
  }


def health_check_response() -> str:
  """Generate health check response for HTTP endpoint.

  Returns:
      str: Health check response in JSON format
  """
  import json

  health = get_overall_health()
  return json.dumps(health, indent=2)


# Export all public symbols
__all__ = [
  "check_github_health",
  "check_jenkins_health",
  "check_azure_health",
  "check_artifactory_health",
  "check_cache_health",
  "get_overall_health",
  "health_check_response",
  # Export modules for test patching
  "github",
  "jenkins",
  "azure",
  "azure_auth",
  "artifactory_auth",
  "cache",
]
