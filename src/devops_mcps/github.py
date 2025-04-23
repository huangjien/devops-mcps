# /Users/huangjien/workspace/devops-mcps/src/devops_mcps/github.py
import logging
import os
from typing import List, Optional, Dict, Any, Union
from .cache import cache

# Third-party imports
from github import (
  Github,
  GithubException,
  UnknownObjectException,
  RateLimitExceededException,
  BadCredentialsException,
)
from github.PaginatedList import PaginatedList
from github.Repository import Repository
from github.Commit import Commit
from github.Issue import Issue
from github.ContentFile import ContentFile
from github.NamedUser import NamedUser
from github.GitAuthor import GitAuthor
from github.Label import Label
from github.License import License  # Import License for _to_dict
from github.Milestone import Milestone  # Import Milestone for _to_dict

# --- Import field_validator instead of validator ---
from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)

# --- Pydantic Models (Input Validation - Moved from core.py) ---


class SearchRepositoriesInput(BaseModel):
  query: str


class GetFileContentsInput(BaseModel):
  owner: str
  repo: str
  path: str
  branch: Optional[str] = None


class ListCommitsInput(BaseModel):
  owner: str
  repo: str
  branch: Optional[str] = None


class ListIssuesInput(BaseModel):
  owner: str
  repo: str
  state: str = "open"
  labels: Optional[List[str]] = None
  sort: str = "created"
  direction: str = "desc"

  # --- Use field_validator ---
  @field_validator("state")
  @classmethod  # Keep classmethod if needed, often optional in v2 for simple validators
  def state_must_be_valid(cls, v: str) -> str:
    if v not in ["open", "closed", "all"]:
      raise ValueError("state must be 'open', 'closed', or 'all'")
    return v

  # --- Use field_validator ---
  @field_validator("sort")
  @classmethod
  def sort_must_be_valid(cls, v: str) -> str:
    if v not in ["created", "updated", "comments"]:
      raise ValueError("sort must be 'created', 'updated', or 'comments'")
    return v

  # --- Use field_validator ---
  @field_validator("direction")
  @classmethod
  def direction_must_be_valid(cls, v: str) -> str:
    if v not in ["asc", "desc"]:
      raise ValueError("direction must be 'asc' or 'desc'")
    return v


class GetRepositoryInput(BaseModel):
  owner: str
  repo: str


class SearchCodeInput(BaseModel):
  q: str
  sort: str = "indexed"
  order: str = "desc"

  # --- Use field_validator ---
  @field_validator("sort")
  @classmethod
  def sort_must_be_valid(cls, v: str) -> str:
    # Note: The original logic used 'pass', which doesn't do anything.
    # If validation is intended, it should raise an error or modify the value.
    # Keeping the original intent (allowing 'indexed' or 'best match' implicitly).
    # If strict validation was intended, add:
    # if v not in ['indexed', 'best match']:
    #     raise ValueError("sort must be 'indexed' or 'best match'")
    return v

  # --- Use field_validator ---
  @field_validator("order")
  @classmethod
  def order_must_be_valid(cls, v: str) -> str:
    if v not in ["asc", "desc"]:
      raise ValueError("order must be 'asc' or 'desc'")
    return v


# --- GitHub Client Initialization ---

GITHUB_TOKEN = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
GITHUB_API_URL = os.environ.get(
  "GITHUB_API_URL"
)  # e.g., https://github.mycompany.com/api/v3
g: Optional[Github] = None


def initialize_github_client():
  """Initializes the global GitHub client 'g'."""
  global g
  if g:  # Already initialized
    return g

  github_kwargs = {"timeout": 60, "per_page": 10}
  if GITHUB_API_URL:
    github_kwargs["base_url"] = GITHUB_API_URL
  else:
    github_kwargs["base_url"] = "https://api.github.com/api/v3"  # Default

  if GITHUB_TOKEN:
    try:
      g = Github(GITHUB_TOKEN, **github_kwargs)
      _ = g.get_user().login  # Test connection
      logger.info(
        f"Authenticated with GitHub using GITHUB_PERSONAL_ACCESS_TOKEN. Base URL: {github_kwargs.get('base_url', 'default')}"
      )
    except RateLimitExceededException:
      logger.error("GitHub API rate limit exceeded during initialization.")
      g = None
    except BadCredentialsException:
      logger.error("Invalid GitHub Personal Access Token provided.")
      g = None
    except Exception as e:
      logger.error(f"Failed to initialize authenticated GitHub client: {e}")
      g = None
  else:
    logger.warning("GITHUB_PERSONAL_ACCESS_TOKEN environment variable not set.")
    logger.warning("GitHub related tools will have limited functionality.")
    try:
      g = Github(**github_kwargs)
      _ = g.get_rate_limit()  # Basic check
      logger.info(
        f"Initialized unauthenticated GitHub client. Base URL: {github_kwargs.get('base_url', 'default')}"
      )
    except Exception as e:
      logger.error(f"Failed to initialize unauthenticated GitHub client: {e}")
      g = None
  return g


# Call initialization when the module is loaded
initialize_github_client()

# --- Helper Functions for Object Conversion (to Dict) ---


def _to_dict(obj: Any) -> Any:
  """Converts common PyGithub objects to dictionaries. Handles basic types and lists."""
  if isinstance(obj, (str, int, float, bool, type(None))):
    return obj
  if isinstance(obj, list):
    return [_to_dict(item) for item in obj]
  if isinstance(obj, dict):
    return {k: _to_dict(v) for k, v in obj.items()}

  # Add more specific PyGithub object handling as needed
  if isinstance(obj, Repository):
    return {
      "full_name": obj.full_name,
      "name": obj.name,
      "description": obj.description,
      "html_url": obj.html_url,
      #   "homepage": obj.homepage,
      "language": obj.language,
      #   "stargazers_count": obj.stargazers_count,
      #   "forks_count": obj.forks_count,
      #   "subscribers_count": obj.subscribers_count,
      #   "open_issues_count": obj.open_issues_count,
      #   "license": _to_dict(obj.license) if obj.license else None,
      "private": obj.private,
      #   "created_at": str(obj.created_at) if obj.created_at else None,
      #   "updated_at": str(obj.updated_at) if obj.updated_at else None,
      #   "pushed_at": str(obj.pushed_at) if obj.pushed_at else None,
      "default_branch": obj.default_branch,
      #   "topics": topics,
      "owner_login": obj.owner.login if obj.owner else None,  # Simplified owner
      # Add other relevant fields as needed
    }
  if isinstance(obj, Commit):
    commit_data = obj.commit
    return {
      "sha": obj.sha,
      "html_url": obj.html_url,
      "message": commit_data.message if commit_data else None,
      # Simplified author/committer info from GitAuthor
      "author": _to_dict(commit_data.author)
      if commit_data and commit_data.author
      else None,
      # Removed committer, api_author, api_committer, parents based on previous suggestion
    }
  if isinstance(obj, Issue):
    return {
      "number": obj.number,
      "title": obj.title,
      "state": obj.state,
      "html_url": obj.html_url,
      # Removed body based on previous suggestion
      "user_login": obj.user.login if obj.user else None,  # Simplified user
      "label_names": [label.name for label in obj.labels],  # Simplified labels
      "assignee_logins": [a.login for a in obj.assignees]
      if obj.assignees
      else ([obj.assignee.login] if obj.assignee else []),  # Simplified assignees
      # Removed milestone, comments count, timestamps, closed_by based on previous suggestion
      "is_pull_request": obj.pull_request is not None,
    }
  if isinstance(obj, ContentFile):
    # Basic info suitable for listings and search results
    repo_name = None
    if hasattr(obj, "repository") and obj.repository:
      repo_name = obj.repository.full_name

    return {
      "type": obj.type,
      "name": obj.name,
      "path": obj.path,
      "size": obj.size,
      "html_url": obj.html_url,
      "repository_full_name": repo_name,  # Simplified repository info
      # Removed sha, download_url, encoding based on previous suggestion
    }
  if isinstance(obj, NamedUser):
    # Simplified based on previous suggestion
    return {
      "login": obj.login,
      "html_url": obj.html_url,
      "type": obj.type,
    }
  if isinstance(obj, GitAuthor):
    # Simplified based on previous suggestion
    return {
      "name": obj.name,
      # "email": obj.email, # Removed email
      "date": str(obj.date) if obj.date else None,
    }
  if isinstance(obj, Label):
    # Simplified based on previous suggestion
    return {"name": obj.name}  # Keep only name
    # return {"name": obj.name, "color": obj.color, "description": obj.description} # Original
  if isinstance(obj, License):
    # Simplified based on previous suggestion
    return {"name": obj.name, "spdx_id": obj.spdx_id}  # Keep only name and spdx_id
    # return {"key": obj.key, "name": obj.name, "spdx_id": obj.spdx_id, "url": obj.url} # Original
  if isinstance(obj, Milestone):
    # Simplified based on previous suggestion
    return {
      "title": obj.title,
      "state": obj.state,
      # "creator_login": obj.creator.login if obj.creator else None, # Simplified creator
      # Removed id, number, description, counts, timestamps
    }
    # Original:
    # return {
    #   "id": obj.id, "number": obj.number, "title": obj.title, "state": obj.state,
    #   "description": obj.description, "creator": _to_dict(obj.creator),
    #   "open_issues": obj.open_issues, "closed_issues": obj.closed_issues,
    #   "created_at": str(obj.created_at) if obj.created_at else None,
    #   "due_on": str(obj.due_on) if obj.due_on else None,
    # }

  # Fallback
  try:
    if hasattr(obj, "_rawData"):
      # Optionally filter rawData too, but can be complex
      # For now, return raw if specific handling isn't defined
      logger.debug(f"Using rawData fallback for type {type(obj).__name__}")
      return obj._rawData
    # Avoid using vars() as it's often not helpful for complex objects
    logger.warning(
      f"No specific _to_dict handler for type {type(obj).__name__}, returning string representation."
    )
    return f"<Object of type {type(obj).__name__}>"
  except Exception as fallback_err:  # Catch potential errors during fallback
    logger.error(
      f"Error during fallback _to_dict for {type(obj).__name__}: {fallback_err}"
    )
    return f"<Error serializing object of type {type(obj).__name__}>"


def _handle_paginated_list(paginated_list: PaginatedList) -> List[Dict[str, Any]]:
  """Converts items from the first page of a PaginatedList to dictionaries."""
  try:
    # Fetching the first page is implicit when iterating or slicing
    # We limit to the client's per_page setting (e.g., 100) by default
    first_page_items = paginated_list.get_page(0)
    logger.debug(
      f"Processing {len(first_page_items)} items from paginated list (type: {type(paginated_list._PaginatedList__type).__name__ if hasattr(paginated_list, '_PaginatedList__type') else 'Unknown'})"
    )
    return [_to_dict(item) for item in first_page_items]
  except Exception as e:
    logger.error(f"Error processing PaginatedList: {e}", exc_info=True)
    # Return an error structure or an empty list
    return [{"error": f"Failed to process results: {e}"}]


# --- GitHub API Functions (Internal Logic) ---
# These functions contain the core PyGithub interaction logic


def gh_search_repositories(query: str) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Internal logic for searching repositories."""
  logger.debug(f"gh_search_repositories called with query: '{query}'")
  
  # Check cache first
  cache_key = f"github:search_repos:{query}"
  cached = cache.get(cache_key)
  if cached:
    logger.debug(f"Returning cached result for {cache_key}")
    return cached
    
  if not g:
    logger.error("gh_search_repositories: GitHub client not initialized.")
    return {"error": "GitHub client not initialized."}
  try:
    input_data = SearchRepositoriesInput(query=query)
    repositories: PaginatedList = g.search_repositories(query=input_data.query)
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
    
  if not g:
    logger.error("gh_get_file_contents: GitHub client not initialized.")
    return {"error": "GitHub client not initialized."}
  try:
    input_data = GetFileContentsInput(owner=owner, repo=repo, path=path, branch=branch)
    repo_obj = g.get_repo(f"{input_data.owner}/{input_data.repo}")
    ref_kwarg = {"ref": input_data.branch} if input_data.branch else {}
    contents = repo_obj.get_contents(input_data.path, **ref_kwarg)

    if isinstance(contents, list):  # Directory
      logger.debug(f"Path '{path}' is a directory with {len(contents)} items.")
      return [_to_dict(item) for item in contents]
    else:  # File
      logger.debug(
        f"Path '{path}' is a file (size: {contents.size}, encoding: {contents.encoding})."
      )
      if contents.encoding == "base64" and contents.content:
        try:
          decoded = contents.decoded_content.decode("utf-8")
          logger.debug(f"Successfully decoded base64 content for '{path}'.")
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
    
  if not g:
    logger.error("gh_list_commits: GitHub client not initialized.")
    return {"error": "GitHub client not initialized."}
  try:
    input_data = ListCommitsInput(owner=owner, repo=repo, branch=branch)
    repo_obj = g.get_repo(f"{input_data.owner}/{input_data.repo}")
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
  cache_key = f"github:list_issues:{owner}/{repo}:{state}:{labels_str}:{sort}:{direction}"
  cached = cache.get(cache_key)
  if cached:
    logger.debug(f"Returning cached result for {cache_key}")
    return cached
    
  if not g:
    logger.error("gh_list_issues: GitHub client not initialized.")
    return {"error": "GitHub client not initialized."}
  try:
    input_data = ListIssuesInput(
      owner=owner, repo=repo, state=state, labels=labels, sort=sort, direction=direction
    )
    repo_obj = g.get_repo(f"{input_data.owner}/{input_data.repo}")
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
    
  if not g:
    logger.error("gh_get_repository: GitHub client not initialized.")
    return {"error": "GitHub client not initialized."}
  try:
    input_data = GetRepositoryInput(owner=owner, repo=repo)
    repo_obj = g.get_repo(f"{input_data.owner}/{input_data.repo}")
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
    
  if not g:
    logger.error("gh_search_code: GitHub client not initialized.")
    return {"error": "GitHub client not initialized."}
  try:
    input_data = SearchCodeInput(q=q, sort=sort, order=order)
    search_kwargs = {"sort": input_data.sort, "order": input_data.order}
    code_results: PaginatedList = g.search_code(query=input_data.q, **search_kwargs)
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
