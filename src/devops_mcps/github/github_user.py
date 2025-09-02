"""GitHub user operations module."""

import logging
from typing import Any, Dict

from github.GithubException import GithubException, BadCredentialsException

from .cache import github_cache
from .github_client import get_github_client
from .github_serializers import _to_dict
from .inputs import GetCurrentUserInfoInput

logger = logging.getLogger(__name__)


@github_cache(expire=300)
def gh_get_current_user_info(input_data: GetCurrentUserInfoInput) -> Dict[str, Any]:
    """
    Get information about the currently authenticated GitHub user.
    
    Args:
        input_data: GetCurrentUserInfoInput (currently unused but kept for consistency).
        
    Returns:
        Dict[str, Any]: User information.
        
    Raises:
        GithubException: If the GitHub API request fails.
    """
    try:
        g = get_github_client()
        user = g.get_user()
        
        return _to_dict(user)
    
    except ValueError as e:
        # Handle case when GitHub client is not initialized
        if "GitHub client not initialized" in str(e):
            logger.error(f"GitHub client not initialized in get_current_user_info: {e}")
            return {"error": "GitHub client not initialized. Please set GITHUB_TOKEN environment variable."}
        logger.error(f"ValueError in get_current_user_info: {e}")
        return {"error": f"Configuration error: {e}"}
    except BadCredentialsException as e:
        logger.error(f"GitHub API error in get_current_user_info: {e}")
        return {"error": "Authentication failed"}
    except GithubException as e:
        logger.error(f"GitHub API error in get_current_user_info: {e}")
        status_code = getattr(e, 'status', 'Unknown')
        message = getattr(e, 'data', {}).get('message', 'Unknown GitHub error') if hasattr(e, 'data') and e.data else 'Unknown GitHub error'
        return {"error": f"GitHub API Error: {status_code} - {message}"}
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user_info: {e}")
        return {"error": f"unexpected error: {e}"}