"""GitHub search operations module.

This module provides functions for searching GitHub repositories and code.
"""

import logging
from typing import Any, Dict

from github.GithubException import GithubException
from github import RateLimitExceededException

from .cache import github_cache
from .github_client import get_github_client
from .github_serializers import _handle_paginated_list
from .inputs import SearchCodeInput

logger = logging.getLogger(__name__)


@github_cache(expire=300)
def gh_search_code(input_data: SearchCodeInput) -> Dict[str, Any]:
    """
    Search for code across GitHub repositories.
    
    Args:
        input_data: SearchCodeInput containing search parameters.
        
    Returns:
        Dict[str, Any]: Search results with metadata.
        
    Raises:
        GithubException: If the GitHub API request fails.
    """
    logger.debug(f"gh_search_code called with query: '{input_data.q}'")
    try:
        g = get_github_client()
        
        # Build search query
        query_parts = [input_data.q]
        
        if input_data.repo:
            query_parts.append(f"repo:{input_data.repo}")
        
        if input_data.language:
            query_parts.append(f"language:{input_data.language}")
        
        if input_data.filename:
            query_parts.append(f"filename:{input_data.filename}")
        
        if input_data.extension:
            query_parts.append(f"extension:{input_data.extension}")
        
        if input_data.path:
            query_parts.append(f"path:{input_data.path}")
        
        if input_data.size:
            query_parts.append(f"size:{input_data.size}")
        
        if input_data.user:
            query_parts.append(f"user:{input_data.user}")
        
        if input_data.org:
            query_parts.append(f"org:{input_data.org}")
        
        query = " ".join(query_parts)
        
        # Perform search
        search_results = g.search_code(
            query=query,
            sort=input_data.sort,
            order=input_data.order
        )
        
        logger.debug(f"Found {search_results.totalCount} code results matching query")
        
        # Convert to list with pagination
        max_items = input_data.per_page or 30
        items = _handle_paginated_list(search_results, max_items=max_items)
        
        return {
            "total_count": search_results.totalCount,
            "incomplete_results": getattr(search_results, 'incomplete_results', False),
            "items": items
        }
    
    except ValueError as e:
        logger.error(f"Invalid input for code search: {e}")
        return {"error": f"Invalid input: {e}"}
    except RateLimitExceededException as e:
        # Handle rate limit exceptions specifically
        message = ""
        if hasattr(e, 'data') and e.data:
            message = e.data.get('message', 'API rate limit exceeded')
        logger.error(f"Rate limit exceeded during code search: {e}")
        return {"error": f"GitHub API Error: 403 - {message}"}
    except GithubException as e:
        # Handle other GitHub exceptions
        status_code = getattr(e, 'status', None)
        
        if status_code == 401:
            logger.error(f"Authentication error during code search: {e}")
            return {"error": "Authentication required"}
        elif status_code == 403:
            logger.error(f"Forbidden error during code search: {e}")
            return {"error": "Authentication required or insufficient permissions"}
        elif status_code == 422:
            logger.error(f"Invalid query during code search: {e}")
            return {"error": "Invalid search query"}
        else:
            # For other status codes, use the generic format
            message = "Unknown GitHub error"
            if hasattr(e, 'data') and e.data:
                message = e.data.get('message', 'Unknown GitHub error')
            
            logger.error(f"GitHub API error during code search: {status_code} - {message}")
            return {"error": f"GitHub API Error: {status_code} - {message}"}
    except Exception as e:
        # For non-GitHub exceptions
        logger.error(f"Unexpected error during code search: {e}")
        return {"error": "unexpected error"}