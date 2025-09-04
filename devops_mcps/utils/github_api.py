"""Core GitHub API functions."""

import logging
import os
from typing import List, Optional, Dict, Any, Union

from github import (
    GithubException,
    UnknownObjectException,
    RateLimitExceededException,
    BadCredentialsException,
)
from github.PaginatedList import PaginatedList

from ..cache import cache
from ..inputs import (
    SearchRepositoriesInput,
    GetFileContentsInput,
    ListCommitsInput,
    ListIssuesInput,
    GetRepositoryInput,
    SearchCodeInput,
)
from .github_client import initialize_github_client
from .github_converters import _to_dict, _handle_paginated_list

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


def gh_list_commits(
    owner: str, repo: str, branch: Optional[str] = None
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
    """Internal logic for listing commits."""
    logger.debug(f"gh_list_commits called for {owner}/{repo}, branch: {branch}")

    # Check cache first
    branch_str = branch if branch else "default"
    cache_key = f"github:list_commits:{owner}/{repo}:{branch_str}"
    cached = cache.get(cache_key)
    if cached:
        logger.debug(f"Returning cached result for {cache_key}")
        return cached

    github_client = initialize_github_client(force=True)
    if not github_client:
        logger.error("gh_list_commits: GitHub client not initialized.")
        return {
            "error": "GitHub client not initialized. Please set the GITHUB_PERSONAL_ACCESS_TOKEN environment variable."
        }
    try:
        input_data = ListCommitsInput(owner=owner, repo=repo, branch=branch)
        repo_obj = github_client.get_repo(f"{input_data.owner}/{input_data.repo}")
        commit_kwargs = {}
        if input_data.branch:
            commit_kwargs["sha"] = input_data.branch
            logger.debug(f"Fetching commits for branch/sha: {input_data.branch}")
        else:
            logger.debug("Fetching commits for default branch.")

        commits_paginated: PaginatedList = repo_obj.get_commits(**commit_kwargs)
        result = _handle_paginated_list(commits_paginated)
        cache.set(cache_key, result, ttl=3600)  # Cache for 1 hour
        return result
    except UnknownObjectException:
        logger.warning(f"gh_list_commits: Repository '{owner}/{repo}' not found.")
        return {"error": f"Repository '{owner}/{repo}' not found."}
    except GithubException as e:
        msg = e.data.get("message", "Unknown GitHub error")
        logger.error(f"gh_list_commits GitHub Error: {e.status} - {e.data}", exc_info=True)
        if e.status == 409 and "Git Repository is empty" in msg:
            logger.warning(f"gh_list_commits: Repository '{owner}/{repo}' is empty.")
            return {"error": f"Repository {owner}/{repo} is empty."}
        # Handle case where branch doesn't exist (might also be UnknownObjectException or specific GithubException)
        if e.status == 404 or (e.status == 422 and "No commit found for SHA" in msg):
            logger.warning(f"Branch or SHA '{branch}' not found in {owner}/{repo}.")
            return {
                "error": f"Branch or SHA '{branch}' not found in repository {owner}/{repo}."
            }
        return {"error": f"GitHub API Error: {e.status} - {msg}"}
    except Exception as e:
        logger.error(f"Unexpected error in gh_list_commits: {e}", exc_info=True)
        return {"error": f"An unexpected error occurred: {e}"}


def gh_list_issues(
    owner: str,
    repo: str,
    state: str = "open",
    labels: Optional[List[str]] = None,
    sort: str = "created",
    direction: str = "desc",
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
    """Internal logic for listing issues."""
    logger.debug(
        f"gh_list_issues called for {owner}/{repo}, state: {state}, labels: {labels}, sort: {sort}, direction: {direction}"
    )

    # Check cache first
    labels_str = ",".join(sorted(labels)) if labels else "none"
    cache_key = (
        f"github:list_issues:{owner}/{repo}:{state}:{labels_str}:{sort}:{direction}"
    )
    cached = cache.get(cache_key)
    if cached:
        logger.debug(f"Returning cached result for {cache_key}")
        return cached

    github_client = initialize_github_client(force=True)
    if not github_client:
        logger.error("gh_list_issues: GitHub client not initialized.")
        return {
            "error": "GitHub client not initialized. Please set the GITHUB_PERSONAL_ACCESS_TOKEN environment variable."
        }
    try:
        input_data = ListIssuesInput(
            owner=owner, repo=repo, state=state, labels=labels, sort=sort, direction=direction
        )
        repo_obj = github_client.get_repo(f"{input_data.owner}/{input_data.repo}")
        issue_kwargs = {
            "state": input_data.state,
            "sort": input_data.sort,
            "direction": input_data.direction,
        }
        if input_data.labels:
            issue_kwargs["labels"] = input_data.labels
            logger.debug(f"Filtering issues by labels: {input_data.labels}")

        issues_paginated: PaginatedList = repo_obj.get_issues(**issue_kwargs)
        logger.debug(f"Found {issues_paginated.totalCount} issues matching criteria.")
        result = _handle_paginated_list(issues_paginated)
        cache.set(cache_key, result, ttl=1800)  # Cache for 30 minutes
        return result
    except UnknownObjectException:
        logger.warning(f"gh_list_issues: Repository '{owner}/{repo}' not found.")
        return {"error": f"Repository '{owner}/{repo}' not found."}
    except GithubException as e:
        logger.error(f"gh_list_issues GitHub Error: {e.status} - {e.data}", exc_info=True)
        # Add specific error handling if needed, e.g., invalid labels
        return {
            "error": f"GitHub API Error: {e.status} - {e.data.get('message', 'Unknown GitHub error')}"
        }
    except Exception as e:
        logger.error(f"Unexpected error in gh_list_issues: {e}", exc_info=True)
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


def gh_get_issue_details(owner: str, repo: str, issue_number: int) -> Dict[str, Any]:
    """Fetches issue details including title, labels, timestamp, description, and comments.

    Args:
        owner: The owner of the repository.
        repo: The name of the repository.
        issue_number: The number of the issue.

    Returns:
        A dictionary containing issue details or an error message.
    """
    logger.debug(f"gh_get_issue_details called for {owner}/{repo} issue #{issue_number}")

    # Check cache first
    cache_key = f"github:issue_details:{owner}:{repo}:{issue_number}"
    cached = cache.get(cache_key)
    if cached:
        logger.debug(f"Returning cached result for {cache_key}")
        return cached

    github_client = initialize_github_client(force=True)
    if not github_client:
        logger.error("gh_get_issue_details: GitHub client not initialized.")
        return {
            "error": "GitHub client not initialized. Please set the GITHUB_PERSONAL_ACCESS_TOKEN environment variable."
        }

    try:
        issue = github_client.get_issue(owner, repo, issue_number)
        comments = issue.get_comments()
        issue_details = {
            "title": issue.title,
            "labels": [label.name for label in issue.labels],
            "timestamp": issue.created_at.isoformat(),
            "description": issue.body,
            "comments": [comment.body for comment in comments],
        }
        logger.debug(
            f"Successfully retrieved issue details for {owner}/{repo} issue #{issue_number}"
        )
        cache.set(cache_key, issue_details, ttl=300)  # Cache for 5 minutes
        return issue_details
    except GithubException as e:
        logger.error(
            f"gh_get_issue_details GitHub Error: {e.status} - {e.data}", exc_info=True
        )
        return {
            "error": f"GitHub API Error: {e.status} - {e.data.get('message', 'Unknown GitHub error')}"
        }
    except Exception as e:
        logger.error(f"Unexpected error in gh_get_issue_details: {e}", exc_info=True)
        return {"error": f"An unexpected error occurred: {e}"}


def gh_get_issue_content(owner: str, repo: str, issue_number: int) -> dict:
    """Fetches issue content including title, labels, timestamp, description, and comments.

    Args:
        owner: The owner of the repository.
        repo: The name of the repository.
        issue_number: The number of the issue.

    Returns:
        A dictionary containing issue content or an error message.
    """
    logger.debug(f"gh_get_issue_content called for {owner}/{repo} issue #{issue_number}")

    # Check cache first
    cache_key = f"github:issue_content:{owner}:{repo}:{issue_number}"
    cached = cache.get(cache_key)
    if cached:
        logger.debug(f"Returning cached result for {cache_key}")
        return cached

    github_client = initialize_github_client(force=True)
    if not github_client:
        logger.error("gh_get_issue_content: GitHub client not initialized.")
        return {
            "error": "GitHub client not initialized. Please set the GITHUB_PERSONAL_ACCESS_TOKEN environment variable."
        }

    try:
        repo_obj = github_client.get_repo(f"{owner}/{repo}")
        issue = repo_obj.get_issue(issue_number)
        comments = issue.get_comments()
        issue_content = {
            "title": issue.title,
            "labels": [label.name for label in issue.labels],
            "timestamp": issue.created_at.isoformat(),
            "description": issue.body,
            "comments": [comment.body for comment in comments],
        }
        logger.debug(
            f"Successfully retrieved issue content for {owner}/{repo} issue #{issue_number}"
        )
        cache.set(cache_key, issue_content, ttl=300)  # Cache for 5 minutes
        return issue_content
    except UnknownObjectException:
        logger.warning(
            f"gh_get_issue_content: Repository '{owner}/{repo}' or issue #{issue_number} not found."
        )
        return {
            "error": f"Repository '{owner}/{repo}' or issue #{issue_number} not found."
        }
    except GithubException as e:
        logger.error(
            f"gh_get_issue_content GitHub Error: {e.status} - {e.data}", exc_info=True
        )
        return {
            "error": f"GitHub API Error: {e.status} - {e.data.get('message', 'Unknown GitHub error')}"
        }
    except Exception as e:
        logger.error(f"Unexpected error in gh_get_issue_content: {e}", exc_info=True)
        return {"error": f"An unexpected error occurred: {e}"}