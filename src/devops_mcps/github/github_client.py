"""GitHub client initialization and configuration module.

This module handles the initialization and configuration of the GitHub client,
including authentication and error handling.
"""

import logging
import os
from typing import Optional

from github import Github, Auth
from github.GithubException import BadCredentialsException, RateLimitExceededException

# Configure logging
logger = logging.getLogger(__name__)

# Global variables for GitHub client
g: Optional[Github] = None
GITHUB_TOKEN: Optional[str] = None
GITHUB_API_URL: str = "https://api.github.com"


def initialize_github_client(force: bool = False) -> Optional[Github]:
    """
    Initialize and return a GitHub client using a personal access token.
    
    Args:
        force: If True, reinitialize the client even if one already exists.
    
    Returns:
        Github: An authenticated GitHub client instance, or None if initialization fails.
    """
    global g, GITHUB_TOKEN
    
    if g is not None and not force:
        return g
    
    try:
        GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
        if not GITHUB_TOKEN:
            logger.warning("GITHUB_TOKEN environment variable is not set")
            return None
        
        # Get API URL from environment or use default
        api_url = os.getenv("GITHUB_API_URL", GITHUB_API_URL)
        
        auth = Auth.Token(GITHUB_TOKEN)
        g = Github(auth=auth, base_url=api_url, timeout=60, per_page=10)
        
        # Test the connection by getting the authenticated user
        user = g.get_user()
        logger.info(f"GitHub client initialized successfully for user: {user.login}")
        
        return g
        
    except BadCredentialsException:
        logger.error("Invalid GitHub token provided.")
        return None
    except RateLimitExceededException:
        logger.error("GitHub API rate limit exceeded during initialization.")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize GitHub client: {e}")
        return None


def get_github_client() -> Github:
    """
    Get the current GitHub client instance, initializing if necessary.
    
    Returns:
        Github: The GitHub client instance.
        
    Raises:
        ValueError: If GitHub client cannot be initialized.
    """
    if g is None:
        client = initialize_github_client()
        if client is None:
            raise ValueError("GitHub client not initialized")
        return client
    return g


def reset_github_client() -> None:
    """
    Reset the GitHub client instance.
    
    This is useful for testing or when switching tokens.
    """
    global g, GITHUB_TOKEN
    g = None
    GITHUB_TOKEN = None