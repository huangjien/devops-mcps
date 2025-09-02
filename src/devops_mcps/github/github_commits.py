"""GitHub commits operations module.

This module provides functions for interacting with GitHub commits,
including listing commits from repositories.
"""

import logging
from typing import Any, Dict

from github.GithubException import GithubException, UnknownObjectException

from .cache import github_cache
from .github_client import get_github_client
from .github_serializers import _handle_paginated_list
from .inputs import ListCommitsInput

logger = logging.getLogger(__name__)


@github_cache(expire=300)
def gh_list_commits(input_data: ListCommitsInput) -> Dict[str, Any]:
    """
    List commits from a GitHub repository.
    
    Args:
        input_data: ListCommitsInput containing repository and filtering parameters.
        
    Returns:
        Dict[str, Any]: List of commits with metadata.
        
    Raises:
        UnknownObjectException: If the repository is not found.
        GithubException: If the GitHub API request fails.
    """
    try:
        g = get_github_client()
        repo = g.get_repo(f"{input_data.owner}/{input_data.repo}")
        
        # Build filter parameters
        kwargs = {}
        
        if input_data.sha:
            kwargs["sha"] = input_data.sha
        
        if input_data.path:
            kwargs["path"] = input_data.path
        
        if input_data.author:
            kwargs["author"] = input_data.author
        
        if input_data.since:
            kwargs["since"] = input_data.since
        
        if input_data.until:
            kwargs["until"] = input_data.until
        
        # Get commits
        commits = repo.get_commits(**kwargs)
        
        # Convert to list with pagination
        max_items = input_data.per_page or 30
        items = _handle_paginated_list(commits, max_items=max_items)
        
        return {
            "total_count": len(items),  # Note: GitHub API doesn't provide total count for repo commits
            "items": items
        }
    
    except UnknownObjectException as e:
        logger.error(f"Repository not found: {e}")
        return {"error": f"Repository not found: {e}"}
    except GithubException as e:
        logger.error(f"GitHub API error in list_commits: {e}")
        status_code = getattr(e, 'status', 'Unknown')
        message = getattr(e, 'data', {}).get('message', 'Unknown GitHub error') if hasattr(e, 'data') and e.data else 'Unknown GitHub error'
        error_message = str(e)
        if "empty" in error_message.lower():
            return {"error": f"Repository is empty: GitHub API Error: {status_code} - {message}"}
        elif "not found" in error_message.lower() or "no commit found" in error_message.lower():
            return {"error": f"Branch or commit not found: GitHub API Error: {status_code} - {message}"}
        else:
            return {"error": f"GitHub API Error: {status_code} - {message}"}
    except ValueError as e:
        logger.error(f"GitHub client error in list_commits: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in list_commits: {e}")
        return {"error": f"unexpected error: {e}"}