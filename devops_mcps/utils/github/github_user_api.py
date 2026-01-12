"""GitHub User API functions."""

import logging
import os
from typing import Dict, Any

from github import (
  GithubException,
  RateLimitExceededException,
  BadCredentialsException,
)

from ...cache import cache
from .github_client import initialize_github_client

logger = logging.getLogger(__name__)


def gh_get_current_user_info() -> Dict[str, Any]:
  """Internal logic for getting the authenticated user's info."""
  logger.debug("gh_get_current_user_info called")

  # Check if token is available first, since this is an authenticated-only endpoint
  github_token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
  if not github_token:
    logger.error("gh_get_current_user_info: No GitHub token provided.")
    return {
      "error": "GitHub client not initialized. Please set the GITHUB_PERSONAL_ACCESS_TOKEN environment variable."
    }

  # Check cache first (optional, but good practice if info doesn't change often)
  cache_key = "github:current_user_info"
  cached = cache.get(cache_key)
  if cached:
    logger.debug(f"Returning cached result for {cache_key}")
    return cached

  github_client = initialize_github_client(force=True)  # Ensure client is initialized
  if not github_client:
    logger.error("gh_get_current_user_info: GitHub client not initialized.")
    return {
      "error": "GitHub client not initialized. Please set the GITHUB_PERSONAL_ACCESS_TOKEN environment variable."
    }

  try:
    user = github_client.get_user()
    user_info = {
      "login": user.login,
      "name": user.name,
      "email": user.email,
      "id": user.id,
      "html_url": user.html_url,
      "type": user.type,
      # Add other fields as needed, e.g., company, location
    }
    logger.debug(f"Successfully retrieved user info for {user.login}")
    cache.set(cache_key, user_info, ttl=3600)  # Cache for 1 hour
    return user_info
  except BadCredentialsException:
    logger.error("gh_get_current_user_info: Invalid credentials.")
    return {"error": "Authentication failed. Check your GitHub token."}
  except RateLimitExceededException:
    logger.error("gh_get_current_user_info: GitHub API rate limit exceeded.")
    return {"error": "GitHub API rate limit exceeded."}
  except GithubException as e:
    logger.error(
      f"gh_get_current_user_info GitHub Error: {e.status} - {e.data}", exc_info=True
    )
    return {
      "error": f"GitHub API Error: {e.status} - {e.data.get('message', 'Unknown GitHub error')}"
    }
  except Exception as e:
    logger.error(f"Unexpected error in gh_get_current_user_info: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"}
