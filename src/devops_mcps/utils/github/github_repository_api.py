"""GitHub Repository API functions.

This module contains functions for interacting with GitHub repositories,
including getting repository information and file contents.
"""

import logging
from typing import List, Optional, Dict, Any, Union

from github import (
  GithubException,
  UnknownObjectException,
)

from ...cache import cache
from ...inputs import (
  GetFileContentsInput,
  GetRepositoryInput,
)
from .github_client import initialize_github_client
from .github_converters import _to_dict

logger = logging.getLogger(__name__)


def gh_get_file_contents(
  owner: str, repo: str, path: str, branch: Optional[str] = None
) -> Union[str, List[Dict[str, Any]], Dict[str, Any]]:
  """Internal logic for getting file/directory contents."""
  logger.debug(
    f"gh_get_file_contents called for {owner}/{repo}/{path}, branch: {branch}"
  )

  # Check cache first
  branch_str = branch if branch else "default"
  cache_key = f"github:get_file:{owner}/{repo}/{path}:{branch_str}"
  cached = cache.get(cache_key)
  if cached:
    logger.debug(f"Returning cached result for {cache_key}")
    return cached

  github_client = initialize_github_client(force=True)
  if not github_client:
    logger.error("gh_get_file_contents: GitHub client not initialized.")
    return {
      "error": "GitHub client not initialized. Please set the GITHUB_PERSONAL_ACCESS_TOKEN environment variable."
    }
  try:
    input_data = GetFileContentsInput(owner=owner, repo=repo, path=path, branch=branch)
    repo_obj = github_client.get_repo(f"{input_data.owner}/{input_data.repo}")
    ref_kwarg = {"ref": input_data.branch} if input_data.branch else {}
    contents = repo_obj.get_contents(input_data.path, **ref_kwarg)

    if isinstance(contents, list):  # Directory
      logger.debug(f"Path '{path}' is a directory with {len(contents)} items.")
      result = [_to_dict(item) for item in contents]
      cache.set(cache_key, result, ttl=1800)
      return result
    else:  # File
      logger.debug(
        f"Path '{path}' is a file (size: {contents.size}, encoding: {contents.encoding})."
      )
      if contents.encoding == "base64" and contents.content:
        try:
          decoded = contents.decoded_content.decode("utf-8")
          logger.debug(f"Successfully decoded base64 content for '{path}'.")
          cache.set(cache_key, decoded, ttl=1800)
          return decoded
        except UnicodeDecodeError:
          logger.warning(
            f"Could not decode base64 content for '{path}' (likely binary)."
          )
          return {
            "error": "Could not decode content (likely binary file).",
            **_to_dict(contents),  # Include metadata
          }
        except Exception as decode_error:
          logger.error(
            f"Error decoding base64 content for '{path}': {decode_error}", exc_info=True
          )
          return {
            "error": f"Error decoding content: {decode_error}",
            **_to_dict(contents),
          }
      elif contents.content is not None:
        logger.debug(f"Returning raw (non-base64) content for '{path}'.")
        result = contents.content  # Return raw if not base64
        cache.set(cache_key, result, ttl=1800)  # Cache for 30 minutes
        return result
      else:
        logger.debug(f"Content for '{path}' is None or empty.")
        result = {
          "message": "File appears to be empty or content is inaccessible.",
          **_to_dict(contents),  # Include metadata
        }
        cache.set(cache_key, result, ttl=1800)  # Cache for 30 minutes
        return result
  except UnknownObjectException:
    logger.warning(
      f"gh_get_file_contents: Repository '{owner}/{repo}' or path '{path}' not found."
    )
    return {"error": f"Repository '{owner}/{repo}' or path '{path}' not found."}
  except GithubException as e:
    msg = e.data.get("message", "Unknown GitHub error")
    logger.error(
      f"gh_get_file_contents GitHub Error: {e.status} - {e.data}", exc_info=True
    )
    if "too large" in msg.lower():
      return {"error": f"File '{path}' is too large to retrieve via the API."}
    return {"error": f"GitHub API Error: {e.status} - {msg}"}
  except Exception as e:
    logger.error(f"Unexpected error in gh_get_file_contents: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"}


def gh_get_repository(owner: str, repo: str) -> Union[Dict[str, Any], Dict[str, str]]:
  """Internal logic for getting repository info."""
  logger.debug(f"gh_get_repository called for {owner}/{repo}")

  # Check cache first
  cache_key = f"github:get_repo:{owner}/{repo}"
  cached = cache.get(cache_key)
  if cached:
    logger.debug(f"Returning cached result for {cache_key}")
    return cached

  github_client = initialize_github_client(force=True)
  if not github_client:
    logger.error("gh_get_repository: GitHub client not initialized.")
    return {
      "error": "GitHub client not initialized. Please set the GITHUB_PERSONAL_ACCESS_TOKEN environment variable."
    }
  try:
    input_data = GetRepositoryInput(owner=owner, repo=repo)
    repo_obj = github_client.get_repo(f"{input_data.owner}/{input_data.repo}")
    logger.debug(f"Successfully retrieved repository object for {owner}/{repo}.")
    result = _to_dict(repo_obj)
    cache.set(cache_key, result, ttl=3600)  # Cache for 1 hour
    return result
  except UnknownObjectException:
    logger.warning(f"gh_get_repository: Repository '{owner}/{repo}' not found.")
    return {"error": f"Repository '{owner}/{repo}' not found."}
  except GithubException as e:
    logger.error(
      f"gh_get_repository GitHub Error: {e.status} - {e.data}", exc_info=True
    )
    return {
      "error": f"GitHub API Error: {e.status} - {e.data.get('message', 'Unknown GitHub error')}"
    }
  except Exception as e:
    logger.error(f"Unexpected error in gh_get_repository: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"}
