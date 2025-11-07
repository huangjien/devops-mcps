"""MCP tools module containing all tool function definitions.

This module defines all the tool functions that can be registered with the FastMCP server.
Each function is defined separately and then registered via the register_tools function.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from . import artifactory, azure, github, jenkins

logger = logging.getLogger(__name__)


# --- Azure Tools ---
async def get_azure_subscriptions() -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Get all Azure subscriptions.

  Returns:
      List of subscription dictionaries or an error dictionary.
  """
  logger.debug("Executing get_azure_subscriptions")
  return azure.get_subscriptions()


async def list_azure_vms(
  subscription_id: str,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """List all virtual machines in an Azure subscription.

  Args:
      subscription_id: Azure subscription ID.

  Returns:
      List of VM dictionaries or an error dictionary.
  """
  logger.debug(f"Executing list_azure_vms for subscription: {subscription_id}")
  if not subscription_id:
    logger.error("Parameter 'subscription_id' cannot be empty")
    return {"error": "Parameter 'subscription_id' cannot be empty"}
  return azure.list_virtual_machines(subscription_id=subscription_id)


async def list_aks_clusters(
  subscription_id: str,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """List all AKS clusters in an Azure subscription.

  Args:
      subscription_id: Azure subscription ID.

  Returns:
      List of AKS cluster dictionaries or an error dictionary.
  """
  logger.debug(f"Executing list_aks_clusters for subscription: {subscription_id}")
  if not subscription_id:
    logger.error("Parameter 'subscription_id' cannot be empty")
    return {"error": "Parameter 'subscription_id' cannot be empty"}
  return azure.list_aks_clusters(subscription_id=subscription_id)


async def list_azure_app_services(
  subscription_id: str,
  resource_group: Optional[str] = None,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """List all App Services in an Azure subscription or resource group.

  Args:
      subscription_id: Azure subscription ID.
      resource_group: Optional resource group name to filter results.

  Returns:
      List of App Service dictionaries or an error dictionary.
  """
  logger.debug(f"Executing list_azure_app_services for subscription: {subscription_id}")
  if not subscription_id:
    logger.error("Parameter 'subscription_id' cannot be empty")
    return {"error": "Parameter 'subscription_id' cannot be empty"}
  return azure.list_app_services(
    subscription_id=subscription_id, resource_group=resource_group
  )


async def get_azure_app_service_details(
  subscription_id: str,
  resource_group: str,
  app_name: str,
) -> Union[Dict[str, Any], Dict[str, str]]:
  """Get detailed information about a specific Azure App Service.

  Args:
      subscription_id: Azure subscription ID.
      resource_group: Resource group name.
      app_name: App Service name.

  Returns:
      App Service details dictionary or an error dictionary.
  """
  logger.debug(f"Executing get_azure_app_service_details for app: {app_name}")
  if not subscription_id:
    logger.error("Parameter 'subscription_id' cannot be empty")
    return {"error": "Parameter 'subscription_id' cannot be empty"}
  if not resource_group:
    logger.error("Parameter 'resource_group' cannot be empty")
    return {"error": "Parameter 'resource_group' cannot be empty"}
  if not app_name:
    logger.error("Parameter 'app_name' cannot be empty")
    return {"error": "Parameter 'app_name' cannot be empty"}
  return azure.get_app_service_details(
    subscription_id=subscription_id, resource_group=resource_group, app_name=app_name
  )


async def get_azure_app_service_metrics(
  subscription_id: str,
  resource_group: str,
  app_name: str,
  time_range: str = "PT1H",
) -> Union[Dict[str, Any], Dict[str, str]]:
  """Get metrics for a specific Azure App Service.

  Args:
      subscription_id: Azure subscription ID.
      resource_group: Resource group name.
      app_name: App Service name.
      time_range: Time range for metrics (ISO 8601 duration format).

  Returns:
      App Service metrics dictionary or an error dictionary.
  """
  logger.debug(f"Executing get_azure_app_service_metrics for app: {app_name}")
  if not subscription_id:
    logger.error("Parameter 'subscription_id' cannot be empty")
    return {"error": "Parameter 'subscription_id' cannot be empty"}
  if not resource_group:
    logger.error("Parameter 'resource_group' cannot be empty")
    return {"error": "Parameter 'resource_group' cannot be empty"}
  if not app_name:
    logger.error("Parameter 'app_name' cannot be empty")
    return {"error": "Parameter 'app_name' cannot be empty"}
  return azure.get_app_service_metrics(
    subscription_id=subscription_id,
    resource_group=resource_group,
    app_name=app_name,
    time_range=time_range,
  )


async def list_azure_app_service_plans(
  subscription_id: str,
  resource_group: Optional[str] = None,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """List all App Service Plans in an Azure subscription or resource group.

  Args:
      subscription_id: Azure subscription ID.
      resource_group: Optional resource group name to filter results.

  Returns:
      List of App Service Plan dictionaries or an error dictionary.
  """
  logger.debug(
    f"Executing list_azure_app_service_plans for subscription: {subscription_id}"
  )
  if not subscription_id:
    logger.error("Parameter 'subscription_id' cannot be empty")
    return {"error": "Parameter 'subscription_id' cannot be empty"}
  return azure.list_app_service_plans(
    subscription_id=subscription_id, resource_group=resource_group
  )


# --- GitHub Tools ---
async def search_repositories(
  query: str,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Search for GitHub repositories.

  Args:
      query: Search query string.

  Returns:
      List of repository dictionaries or an error dictionary.
  """
  logger.debug(f"Executing search_repositories with query: {query}")
  if not query:
    logger.error("Parameter 'query' cannot be empty")
    return {"error": "Parameter 'query' cannot be empty"}
  return github.gh_search_repositories(query=query)


async def github_get_current_user_info() -> Union[Dict[str, Any], Dict[str, str]]:
  """Get current GitHub user information.

  Returns:
      User information dictionary or an error dictionary.
  """
  logger.debug("Executing github_get_current_user_info")
  return github.gh_get_current_user_info()


async def get_file_contents(
  owner: str,
  repo: str,
  path: str,
  branch: Optional[str] = None,
) -> Union[str, Dict[str, str]]:
  """Get the contents of a file from a GitHub repository.

  Args:
      owner: Repository owner.
      repo: Repository name.
      path: File path.
      branch: Branch name (optional).

  Returns:
      File contents as string or an error dictionary.
  """
  logger.debug(f"Executing get_file_contents for {owner}/{repo}/{path}")
  if not owner:
    logger.error("Parameter 'owner' cannot be empty")
    return {"error": "Parameter 'owner' cannot be empty"}
  if not repo:
    logger.error("Parameter 'repo' cannot be empty")
    return {"error": "Parameter 'repo' cannot be empty"}
  if not path:
    logger.error("Parameter 'path' cannot be empty")
    return {"error": "Parameter 'path' cannot be empty"}
  return github.gh_get_file_contents(owner=owner, repo=repo, path=path, branch=branch)


async def list_commits(
  owner: str,
  repo: str,
  branch: Optional[str] = None,
  since: Optional[str] = None,
  until: Optional[str] = None,
  author: Optional[str] = None,
  path: Optional[str] = None,
  per_page: int = 30,
  page: int = 1,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """List commits from a GitHub repository.

  Args:
      owner: Repository owner.
      repo: Repository name.
      branch: Branch name (optional).
      since: Only commits after this date (ISO 8601 format).
      until: Only commits before this date (ISO 8601 format).
      author: GitHub username or email address.
      path: Only commits containing this file path.
      per_page: Number of results per page (default: 30).
      page: Page number (default: 1).

  Returns:
      List of commit dictionaries or an error dictionary.
  """
  logger.debug(f"Executing list_commits for {owner}/{repo}")
  if not owner:
    logger.error("Parameter 'owner' cannot be empty")
    return {"error": "Parameter 'owner' cannot be empty"}
  if not repo:
    logger.error("Parameter 'repo' cannot be empty")
    return {"error": "Parameter 'repo' cannot be empty"}
  return github.gh_list_commits(
    owner=owner,
    repo=repo,
    branch=branch,
    since=since,
    until=until,
    author=author,
    path=path,
    per_page=per_page,
    page=page,
  )


async def list_issues(
  owner: str,
  repo: str,
  state: str = "open",
  labels: Optional[str] = None,
  sort: str = "created",
  direction: str = "desc",
  since: Optional[str] = None,
  per_page: int = 30,
  page: int = 1,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """List issues from a GitHub repository.

  Args:
      owner: Repository owner.
      repo: Repository name.
      state: Issue state (open, closed, all).
      labels: Comma-separated list of label names.
      sort: Sort field (created, updated, comments).
      direction: Sort direction (asc, desc).
      since: Only issues updated after this date (ISO 8601 format).
      per_page: Number of results per page (default: 30).
      page: Page number (default: 1).

  Returns:
      List of issue dictionaries or an error dictionary.
  """
  logger.debug(f"Executing list_issues for {owner}/{repo}")
  if not owner:
    logger.error("Parameter 'owner' cannot be empty")
    return {"error": "Parameter 'owner' cannot be empty"}
  if not repo:
    logger.error("Parameter 'repo' cannot be empty")
    return {"error": "Parameter 'repo' cannot be empty"}
  return github.gh_list_issues(
    owner=owner,
    repo=repo,
    state=state,
    labels=labels,
    sort=sort,
    direction=direction,
    since=since,
    per_page=per_page,
    page=page,
  )


async def get_repository(
  owner: str, repo: str
) -> Union[Dict[str, Any], Dict[str, str]]:
  """Get information about a GitHub repository.

  Args:
      owner: Repository owner.
      repo: Repository name.

  Returns:
      Repository information dictionary or an error dictionary.
  """
  logger.debug(f"Executing get_repository for {owner}/{repo}")
  if not owner:
    logger.error("Parameter 'owner' cannot be empty")
    return {"error": "Parameter 'owner' cannot be empty"}
  if not repo:
    logger.error("Parameter 'repo' cannot be empty")
    return {"error": "Parameter 'repo' cannot be empty"}
  return github.gh_get_repository(owner=owner, repo=repo)


async def search_code(query: str) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Search for code across GitHub repositories.

  Args:
      query: Search query string.

  Returns:
      List of code search result dictionaries or an error dictionary.
  """
  logger.debug(f"Executing search_code with query: {query}")
  if not query:
    logger.error("Parameter 'query' cannot be empty")
    return {"error": "Parameter 'query' cannot be empty"}
  return github.gh_search_code(query=query)


async def get_github_issue_content(owner: str, repo: str, issue_number: int) -> dict:
  """Get the content of a specific GitHub issue.

  Args:
      owner: Repository owner.
      repo: Repository name.
      issue_number: Issue number.

  Returns:
      Issue content dictionary.
  """
  logger.debug(f"Executing get_github_issue_content for {owner}/{repo}#{issue_number}")
  return github.gh_get_issue_content(owner, repo, issue_number)


# --- Jenkins Tools ---
async def get_jenkins_jobs() -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Get all Jenkins jobs.

  Returns:
      List of job dictionaries or an error dictionary.
  """
  logger.debug("Executing get_jenkins_jobs")
  return jenkins.jenkins_get_jobs()


async def get_jenkins_build_log(
  job_name: str, build_number: int
) -> Union[str, Dict[str, str]]:
  """Get the build log for a specific Jenkins job and build number.

  Args:
      job_name: Name of the Jenkins job.
      build_number: Build number.

  Returns:
      Build log as string or an error dictionary.
  """
  logger.debug(f"Executing get_jenkins_build_log for {job_name}#{build_number}")
  if not job_name:
    logger.error("Parameter 'job_name' cannot be empty")
    return {"error": "Parameter 'job_name' cannot be empty"}
  if build_number is None:
    logger.error("Parameter 'build_number' cannot be None")
    return {"error": "Parameter 'build_number' cannot be None"}
  return jenkins.jenkins_get_build_log(job_name=job_name, build_number=build_number)


async def get_all_jenkins_views() -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Get all Jenkins views.

  Returns:
      List of view dictionaries or an error dictionary.
  """
  logger.debug("Executing get_all_jenkins_views")
  return jenkins.jenkins_get_all_views()


async def get_recent_failed_jenkins_builds(
  hours: int = 24,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Get recent failed Jenkins builds within the specified time frame.

  Args:
      hours: Number of hours to look back (default: 24).

  Returns:
      List of failed build dictionaries or an error dictionary.
  """
  logger.debug(f"Executing get_recent_failed_jenkins_builds for last {hours} hours")
  return jenkins.jenkins_get_recent_failed_builds(hours=hours)


# --- Artifactory Tools ---
async def list_artifactory_items(
  repository: str, path: str = "/"
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """List items in an Artifactory repository.

  Args:
      repository: Artifactory repository name.
      path: Path within the repository (default: "/").

  Returns:
      List of item dictionaries or an error dictionary.
  """
  logger.debug(f"Executing list_artifactory_items for {repository}{path}")
  if not repository:
    logger.error("Parameter 'repository' cannot be empty")
    return {"error": "Parameter 'repository' cannot be empty"}
  return artifactory.artifactory_list_items(repository=repository, path=path)


async def search_artifactory_items(
  query: str, repositories: Optional[List[str]] = None
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Search for items in Artifactory.

  Args:
      query: Search query string.
      repositories: List of repository names to search in (optional).

  Returns:
      List of search result dictionaries or an error dictionary.
  """
  logger.debug(f"Executing search_artifactory_items with query: {query}")
  if not query:
    logger.error("Parameter 'query' cannot be empty")
    return {"error": "Parameter 'query' cannot be empty"}
  return artifactory.artifactory_search_items(query=query, repositories=repositories)


async def get_artifactory_item_info(
  repository: str, path: str
) -> Union[Dict[str, Any], Dict[str, str]]:
  """Get information about a specific Artifactory item.

  Args:
      repository: Artifactory repository name.
      path: Path to the item.

  Returns:
      Item information dictionary or an error dictionary.
  """
  logger.debug(f"Executing get_artifactory_item_info for {repository}{path}")
  if not repository:
    logger.error("Parameter 'repository' cannot be empty")
    return {"error": "Parameter 'repository' cannot be empty"}
  if not path:
    logger.error("Parameter 'path' cannot be empty")
    return {"error": "Parameter 'path' cannot be empty"}
  return artifactory.artifactory_get_item_info(repository=repository, path=path)


# --- Cache Management Tool ---
async def clear_cache() -> Dict[str, str]:
  """Clear all cached data from the in-memory cache.

  Returns:
      A dictionary indicating the success status of the cache clearing operation.
  """
  logger.debug("Executing clear_cache")
  try:
    from .cache import cache

    cache.clear()
    logger.info("Cache cleared successfully")
    return {"status": "success", "message": "Cache cleared successfully"}
  except Exception as e:
    logger.error(f"Failed to clear cache: {e}")
    return {"status": "error", "message": f"Failed to clear cache: {e}"}


def register_tools(mcp):
  """Register all MCP tools with the FastMCP server instance.

  Args:
      mcp: FastMCP server instance to register tools with
  """

  # Register Azure tools
  mcp.tool()(get_azure_subscriptions)
  mcp.tool()(list_azure_vms)
  mcp.tool()(list_aks_clusters)
  mcp.tool()(list_azure_app_services)
  mcp.tool()(get_azure_app_service_details)
  mcp.tool()(get_azure_app_service_metrics)
  mcp.tool()(list_azure_app_service_plans)

  # Register GitHub tools
  mcp.tool()(search_repositories)
  mcp.tool()(github_get_current_user_info)
  mcp.tool()(get_file_contents)
  mcp.tool()(list_commits)
  mcp.tool()(list_issues)
  mcp.tool()(get_repository)
  mcp.tool()(search_code)
  mcp.tool()(get_github_issue_content)

  # Register Jenkins tools
  mcp.tool()(get_jenkins_jobs)
  mcp.tool()(get_jenkins_build_log)
  mcp.tool()(get_all_jenkins_views)
  mcp.tool()(get_recent_failed_jenkins_builds)

  # Register Artifactory tools
  mcp.tool()(list_artifactory_items)
  mcp.tool()(search_artifactory_items)
  mcp.tool()(get_artifactory_item_info)

  # Register cache management tool
  mcp.tool()(clear_cache)
