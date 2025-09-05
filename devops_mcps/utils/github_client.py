"""GitHub client initialization and authentication utilities."""

import logging
import os
from typing import Optional

from github import Github, Auth, GithubException

logger = logging.getLogger(__name__)

# Global GitHub client instance
g: Optional[Github] = None
GITHUB_TOKEN = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
GITHUB_API_URL = os.environ.get("GITHUB_API_URL")


def initialize_github_client(force: bool = False) -> Optional[Github]:
  """Initialize and return a GitHub client.

  Args:
      force: If True, force re-initialization even if client already exists.

  Returns:
      Github client instance or None if initialization fails.
  """
  global g

  if g is not None and not force:
    logger.debug("GitHub client already initialized, returning existing instance.")
    return g

  github_token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
  if not github_token:
    logger.error(
      "No GitHub token provided. Set GITHUB_PERSONAL_ACCESS_TOKEN environment variable."
    )
    return None

  try:
    auth = Auth.Token(github_token)
    github_api_url = os.environ.get("GITHUB_API_URL")

    if github_api_url:
      logger.debug(f"Initializing GitHub client with custom API URL: {github_api_url}")
      g = Github(auth=auth, base_url=github_api_url, timeout=60, per_page=10)
    else:
      logger.debug("Initializing GitHub client with default API URL.")
      g = Github(auth=auth, base_url="https://api.github.com", timeout=60, per_page=10)

    # Test the connection
    try:
      user = g.get_user()
      logger.info(f"GitHub client initialized successfully for user: {user.login}")
    except GithubException as e:
      logger.error(f"GitHub authentication test failed: {e.status} - {e.data}")
      g = None
      return None

    return g
  except Exception as e:
    logger.error(f"Failed to initialize GitHub client: {e}", exc_info=True)
    g = None
    return None
