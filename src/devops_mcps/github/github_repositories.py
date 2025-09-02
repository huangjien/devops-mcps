"""GitHub repository operations module.

This module provides functions for interacting with GitHub repositories,
including retrieving repository information, file contents, and searching repositories.
"""

import base64
import logging
from typing import Any, Dict, Union

from github.GithubException import GithubException, UnknownObjectException

from .cache import github_cache
from .github_client import get_github_client
from .github_serializers import _to_dict, _handle_paginated_list
from .inputs import (
    GetFileContentsInput, GetRepositoryInput, SearchRepositoriesInput
)

logger = logging.getLogger(__name__)


@github_cache(expire=300)
def gh_search_repositories(input_data: SearchRepositoriesInput) -> Dict[str, Any]:
    """
    Search for repositories on GitHub.
    
    Args:
        input_data: SearchRepositoriesInput containing search parameters.
        
    Returns:
        Dict[str, Any]: Search results containing repositories and metadata.
        
    Raises:
        GithubException: If the GitHub API request fails.
    """
    try:
        g = get_github_client()
        
        # Build search query
        query_parts = [input_data.query]
        
        if input_data.language:
            query_parts.append(f"language:{input_data.language}")
        
        if input_data.user:
            query_parts.append(f"user:{input_data.user}")
        
        if input_data.org:
            query_parts.append(f"org:{input_data.org}")
        
        if input_data.topic:
            query_parts.append(f"topic:{input_data.topic}")
        
        if input_data.stars:
            query_parts.append(f"stars:{input_data.stars}")
        
        if input_data.forks:
            query_parts.append(f"forks:{input_data.forks}")
        
        if input_data.size:
            query_parts.append(f"size:{input_data.size}")
        
        if input_data.pushed:
            query_parts.append(f"pushed:{input_data.pushed}")
        
        if input_data.created:
            query_parts.append(f"created:{input_data.created}")
        
        if input_data.updated:
            query_parts.append(f"updated:{input_data.updated}")
        
        if input_data.license:
            query_parts.append(f"license:{input_data.license}")
        
        if input_data.is_public is not None:
            visibility = "public" if input_data.is_public else "private"
            query_parts.append(f"is:{visibility}")
        
        if input_data.archived is not None:
            archived_status = "archived" if input_data.archived else "not-archived"
            query_parts.append(f"archived:{archived_status}")
        
        query = " ".join(query_parts)
        
        # Perform search
        repositories = g.search_repositories(
            query=query,
            sort=input_data.sort or "updated",
            order=input_data.order or "desc"
        )
        
        # Convert results
        items = _handle_paginated_list(repositories, max_items=input_data.per_page or 30)
        
        return {
            "total_count": repositories.totalCount,
            "incomplete_results": getattr(repositories, 'incomplete_results', False),
            "items": items
        }
    
    except ValueError as e:
        logger.error(f"GitHub client error in search_repositories: {e}")
        return {"error": str(e)}
    except GithubException as e:
        logger.error(f"GitHub API error in search_repositories: {e}")
        status_code = getattr(e, 'status', 'Unknown')
        message = getattr(e, 'data', {}).get('message', 'Unknown GitHub error') if hasattr(e, 'data') and e.data else 'Unknown GitHub error'
        return {"error": f"GitHub API Error: {status_code} - {message}"}
    except Exception as e:
        logger.error(f"Unexpected error in search_repositories: {e}")
        return {"error": f"unexpected error: {e}"}


@github_cache(expire=300)
def gh_get_file_contents(input_data: GetFileContentsInput) -> Union[str, Dict[str, Any]]:
    """
    Get the contents of a file or directory from a GitHub repository.
    
    Args:
        input_data: GetFileContentsInput containing repository and file information.
        
    Returns:
        Dict[str, Any]: File or directory contents with metadata.
        
    Raises:
        UnknownObjectException: If the repository or file is not found.
        GithubException: If the GitHub API request fails.
    """
    try:
        g = get_github_client()
        repo = g.get_repo(f"{input_data.owner}/{input_data.repo}")
        
        # Get file or directory contents
        contents = repo.get_contents(input_data.path, ref=input_data.branch)
        
        if isinstance(contents, list):
            # Directory contents
            return {
                "type": "directory",
                "path": input_data.path,
                "contents": [_to_dict(item) for item in contents]
            }
        else:
            # Single file - return decoded content as string for files
            if (contents.type == "file" and 
                contents.size < 1024 * 1024):  # 1MB limit
                # Check for empty content
                if contents.content is None:
                    return {"message": "File appears to be empty"}
                
                # Handle base64 encoded content
                if contents.encoding == "base64":
                    try:
                        decoded_content = base64.b64decode(contents.content).decode('utf-8')
                        return decoded_content
                    except (UnicodeDecodeError, ValueError) as e:
                        logger.warning(f"Could not decode file content: {e}")
                        return {"error": f"Could not decode content: {e}"}
                else:
                    # Handle non-base64 encoded content (e.g., utf-8)
                    return contents.content
            
            # For non-text files or large files, return metadata dictionary
            result = _to_dict(contents)
            
            # Ensure result is a dictionary
            if not isinstance(result, dict):
                result = {
                    "name": getattr(contents, 'name', 'unknown'),
                    "path": getattr(contents, 'path', input_data.path),
                    "sha": getattr(contents, 'sha', None),
                    "size": getattr(contents, 'size', 0),
                    "type": "file"
                }
            
            result["type"] = "file"
            return result
    
    except ValueError as e:
        logger.error(f"GitHub client error in get_file_contents: {e}")
        return {"error": str(e)}
    except UnknownObjectException as e:
        logger.error(f"Repository or file not found: {e}")
        return {"error": f"Repository or file not found: {e}"}
    except GithubException as e:
        logger.error(f"GitHub API error in get_file_contents: {e}")
        status_code = getattr(e, 'status', 'Unknown')
        message = getattr(e, 'data', {}).get('message', 'Unknown GitHub error') if hasattr(e, 'data') and e.data else 'Unknown GitHub error'
        return {"error": f"GitHub API Error: {status_code} - {message}"}
    except Exception as e:
        logger.error(f"Unexpected error in get_file_contents: {e}")
        return {"error": f"unexpected error: {e}"}


@github_cache(expire=300)
def gh_get_repository(input_data: GetRepositoryInput) -> Dict[str, Any]:
    """
    Get detailed information about a GitHub repository.
    
    Args:
        input_data: GetRepositoryInput containing repository information.
        
    Returns:
        Dict[str, Any]: Repository information and metadata.
        
    Raises:
        UnknownObjectException: If the repository is not found.
        GithubException: If the GitHub API request fails.
    """
    try:
        g = get_github_client()
        repo = g.get_repo(f"{input_data.owner}/{input_data.repo}")
        
        # Convert repository to dictionary
        repo_dict = _to_dict(repo)
        
        # Add additional information if requested
        if input_data.include_topics:
            repo_dict["topics"] = repo.get_topics()
        
        if input_data.include_languages:
            repo_dict["languages"] = repo.get_languages()
        
        if input_data.include_contributors:
            contributors = _handle_paginated_list(
                repo.get_contributors(), 
                max_items=input_data.max_contributors or 10
            )
            repo_dict["contributors"] = contributors
        
        if input_data.include_releases:
            releases = _handle_paginated_list(
                repo.get_releases(), 
                max_items=input_data.max_releases or 5
            )
            repo_dict["releases"] = releases
        
        if input_data.include_branches:
            branches = _handle_paginated_list(
                repo.get_branches(), 
                max_items=input_data.max_branches or 10
            )
            repo_dict["branches"] = branches
        
        return repo_dict
    
    except ValueError as e:
        logger.error(f"GitHub client error in get_repository: {e}")
        return {"error": str(e)}
    except UnknownObjectException as e:
        logger.error(f"Repository not found: {e}")
        return {"error": f"Repository not found: {e}"}
    except GithubException as e:
        logger.error(f"GitHub API error in get_repository: {e}")
        status_code = getattr(e, 'status', 'Unknown')
        message = getattr(e, 'data', {}).get('message', 'Unknown GitHub error') if hasattr(e, 'data') and e.data else 'Unknown GitHub error'
        return {"error": f"GitHub API Error: {status_code} - {message}"}
    except Exception as e:
        logger.error(f"Unexpected error in get_repository: {e}")
        return {"error": f"unexpected error: {e}"}