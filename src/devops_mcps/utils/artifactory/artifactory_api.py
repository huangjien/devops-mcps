"""Artifactory API functions.

This module provides core API functions for Artifactory operations including
listing items, searching, and getting item information.
"""

import os
import requests
import logging
from typing import Dict, List, Any, Union, Optional

from ...inputs import (
  ListArtifactoryItemsInput,
  SearchArtifactoryItemsInput,
  GetArtifactoryItemInfoInput,
)
from ...cache import cache
from .artifactory_auth import get_auth, validate_artifactory_config

# Initialize logger
logger = logging.getLogger(__name__)


def artifactory_list_items(
  repository: str, path: str = "/"
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """List items under a given repository and path in Artifactory.

  Args:
      repository: The Artifactory repository name
      path: The path within the repository (default: "/")

  Returns:
      List of item dictionaries or an error dictionary
  """
  logger.debug(f"artifactory_list_items called for {repository}/{path}")

  # Check cache first
  cache_key = f"artifactory:list_items:{repository}:{path}"
  cached = cache.get(cache_key)
  if cached:
    logger.debug(f"Returning cached result for {cache_key}")
    return cached

  # Validate configuration
  config_result = validate_artifactory_config()
  if config_result is not True:
    return config_result

  try:
    input_data = ListArtifactoryItemsInput(repository=repository, path=path)

    # Ensure path starts with a slash and doesn't end with one (unless it's the root)
    clean_path = input_data.path
    if not clean_path.startswith("/"):
      clean_path = f"/{clean_path}"
    if clean_path.endswith("/") and clean_path != "/":
      clean_path = clean_path[:-1]

    # Get Artifactory URL from environment
    artifactory_url = os.environ.get("ARTIFACTORY_URL", "")

    # Build the API URL
    api_url = (
      f"{artifactory_url.rstrip('/')}/api/storage/{input_data.repository}{clean_path}"
    )

    # Make the API request
    auth = get_auth()
    if isinstance(auth, dict):  # Identity token or API key
      response = requests.get(api_url, headers=auth)
    else:  # Basic auth
      response = requests.get(api_url, auth=auth)

    if response.status_code == 200:
      data = response.json()
      # Extract the children items if present
      if "children" in data:
        result = data["children"]
        cache.set(cache_key, result, ttl=300)  # Cache for 5 minutes
        return result
      else:
        # If no children, return the item info
        result = {
          "uri": data.get("uri", ""),
          "created": data.get("created", ""),
          "size": data.get("size", 0),
        }
        cache.set(cache_key, result, ttl=300)
        return result
    else:
      error_msg = f"Artifactory API Error: {response.status_code} - {response.text}"
      logger.error(error_msg)
      return {"error": error_msg}

  except Exception as e:
    logger.error(f"Unexpected error in artifactory_list_items: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"}


def artifactory_search_items(
  query: str, repositories: Optional[List[str]] = None
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Search for items across multiple repositories in Artifactory.

  Args:
      query: The search query
      repositories: Optional list of repositories to search in (if None, searches all)

  Returns:
      List of search result dictionaries or an error dictionary
  """
  logger.debug(
    f"artifactory_search_items called with query: '{query}', repositories: {repositories}"
  )

  # Check cache first
  repos_str = ",".join(sorted(repositories)) if repositories else "all"
  cache_key = f"artifactory:search_items:{query}:{repos_str}"
  cached = cache.get(cache_key)
  if cached:
    logger.debug(f"Returning cached result for {cache_key}")
    return cached

  # Validate configuration
  config_result = validate_artifactory_config()
  if config_result is not True:
    return config_result

  try:
    input_data = SearchArtifactoryItemsInput(query=query, repositories=repositories)

    # Get Artifactory URL from environment
    artifactory_url = os.environ.get("ARTIFACTORY_URL", "")

    # Build the API URL
    api_url = f"{artifactory_url.rstrip('/')}/api/search/aql"

    # Construct the AQL query
    aql_query = f'items.find({{"$or":[{{"name":{{"$match":"*{input_data.query}*"}}}},{{"path":{{"$match":"*{input_data.query}*"}}}}]}}'

    # Add repository filter if specified
    if input_data.repositories:
      repo_conditions = [f'{{"repo":"{repo}"}}' for repo in input_data.repositories]
      repo_filter = f'{{"$or":[{",".join(repo_conditions)}]}}'
      aql_query = f'items.find({{"$and":[{{"$or":[{{"name":{{"$match":"*{input_data.query}*"}}}},{{"path":{{"$match":"*{input_data.query}*"}}}}]}},{repo_filter}]}}'

    # Make the API request
    auth = get_auth()
    headers = {"Content-Type": "text/plain"}
    if isinstance(auth, dict):  # Identity token or API key
      headers.update(auth)
      response = requests.post(api_url, data=aql_query, headers=headers)
    else:  # Basic auth
      response = requests.post(api_url, data=aql_query, headers=headers, auth=auth)

    if response.status_code == 200:
      data = response.json()
      result = data.get("results", [])
      cache.set(cache_key, result, ttl=300)  # Cache for 5 minutes
      return result
    else:
      error_msg = f"Artifactory API Error: {response.status_code} - {response.text}"
      logger.error(error_msg)
      return {"error": error_msg}

  except Exception as e:
    logger.error(f"Unexpected error in artifactory_search_items: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"}


def artifactory_get_item_info(
  repository: str, path: str
) -> Union[Dict[str, Any], Dict[str, str]]:
  """Get information about a specific item in Artifactory.

  Args:
      repository: The Artifactory repository name
      path: The path to the item within the repository

  Returns:
      Item information dictionary or an error dictionary
  """
  logger.debug(f"artifactory_get_item_info called for {repository}/{path}")

  # Check cache first
  cache_key = f"artifactory:get_item_info:{repository}:{path}"
  cached = cache.get(cache_key)
  if cached:
    logger.debug(f"Returning cached result for {cache_key}")
    return cached

  # Validate configuration
  config_result = validate_artifactory_config()
  if config_result is not True:
    return config_result

  try:
    input_data = GetArtifactoryItemInfoInput(repository=repository, path=path)

    # Ensure path starts with a slash
    clean_path = input_data.path
    if not clean_path.startswith("/"):
      clean_path = f"/{clean_path}"

    # Get Artifactory URL from environment
    artifactory_url = os.environ.get("ARTIFACTORY_URL", "")

    # Build the API URL for item info
    api_url = (
      f"{artifactory_url.rstrip('/')}/api/storage/{input_data.repository}{clean_path}"
    )

    # Make the API request
    auth = get_auth()
    if isinstance(auth, dict):  # Identity token or API key
      response = requests.get(api_url, headers=auth)
    else:  # Basic auth
      response = requests.get(api_url, auth=auth)

    if response.status_code == 200:
      result = response.json()

      # If it's a file, also get the properties
      if "children" not in result:
        props_url = f"{api_url}?properties"
        if isinstance(auth, dict):  # Identity token or API key
          props_response = requests.get(props_url, headers=auth)
        else:  # Basic auth
          props_response = requests.get(props_url, auth=auth)

        if props_response.status_code == 200:
          props_data = props_response.json()
          result["properties"] = props_data.get("properties", {})

      cache.set(cache_key, result, ttl=300)  # Cache for 5 minutes
      return result
    else:
      error_msg = f"Artifactory API Error: {response.status_code} - {response.text}"
      logger.error(error_msg)
      return {"error": error_msg}

  except Exception as e:
    logger.error(f"Unexpected error in artifactory_get_item_info: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"}
