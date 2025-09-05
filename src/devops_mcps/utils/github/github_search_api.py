"""GitHub Search API functions.

This module contains functions for searching GitHub repositories and code.
"""

import logging
from typing import List, Dict, Any, Union

from github import GithubException
from github.PaginatedList import PaginatedList

from ...cache import cache
from ...inputs import (
  SearchRepositoriesInput,
  SearchCodeInput,
)
from .github_client import initialize_github_client
from .github_converters import _handle_paginated_list

logger = logging.getLogger(__name__)


def gh_search_repositories(
  query: str,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Internal logic for searching repositories."""
  logger.debug(f"gh_search_repositories called with query: '{query}'")

  # Check cache first
  cache_key = f"github:search_repos:{query}"
  cached = cache.get(cache_key)
  if cached:
    logger.debug(f"Returning cached result for {cache_key}")
    return cached

  github_client = initialize_github_client(force=True)
  if not github_client:
    logger.error("gh_search_repositories: GitHub client not initialized.")
    return {
      "error": "GitHub client not initialized. Please set the GITHUB_PERSONAL_ACCESS_TOKEN environment variable."
    }
  try:
    input_data = SearchRepositoriesInput(query=query)
    repositories: PaginatedList = github_client.search_repositories(
      query=input_data.query
    )
    logger.debug(f"Found {repositories.totalCount} repositories matching query.")
    result = _handle_paginated_list(repositories)
    cache.set(cache_key, result, ttl=300)  # Cache for 5 minutes
    return result
  except GithubException as e:
    logger.error(
      f"gh_search_repositories GitHub Error: {e.status} - {e.data}", exc_info=True
    )
    return {
      "error": f"GitHub API Error: {e.status} - {e.data.get('message', 'Unknown GitHub error')}"
    }
  except Exception as e:
    logger.error(f"Unexpected error in gh_search_repositories: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"}


def gh_search_code(
  q: str, sort: str = "indexed", order: str = "desc"
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Internal logic for searching code."""
  logger.debug(f"gh_search_code called with query: '{q}', sort: {sort}, order: {order}")

  # Check cache first
  cache_key = f"github:search_code:{q}:{sort}:{order}"
  cached = cache.get(cache_key)
  if cached:
    logger.debug(f"Returning cached result for {cache_key}")
    return cached

  github_client = initialize_github_client(force=True)
  if not github_client:
    logger.error("gh_search_code: GitHub client not initialized.")
    return {
      "error": "GitHub client not initialized. Please set the GITHUB_PERSONAL_ACCESS_TOKEN environment variable."
    }
  try:
    input_data = SearchCodeInput(q=q, sort=sort, order=order)
    search_kwargs = {"sort": input_data.sort, "order": input_data.order}
    code_results: PaginatedList = github_client.search_code(
      query=input_data.q, **search_kwargs
    )
    logger.debug(f"Found {code_results.totalCount} code results matching query.")
    result = _handle_paginated_list(code_results)
    cache.set(cache_key, result, ttl=300)  # Cache for 5 minutes
    return result
  except GithubException as e:
    msg = e.data.get("message", "Unknown GitHub error")
    logger.error(f"gh_search_code GitHub Error: {e.status} - {e.data}", exc_info=True)
    if e.status in [401, 403]:
      return {"error": f"Authentication required or insufficient permissions. {msg}"}
    if e.status == 422:  # Often invalid query syntax
      return {"error": f"Invalid search query or parameters. {msg}"}
    return {"error": f"GitHub API Error: {e.status} - {msg}"}
  except Exception as e:
    logger.error(f"Unexpected error in gh_search_code: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"}
