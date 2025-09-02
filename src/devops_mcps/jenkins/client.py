"""
Jenkins client initialization and configuration module.
Handles client setup, authentication, and global client management.
"""

import logging
import os
from typing import Optional

from jenkinsapi.jenkins import Jenkins
from jenkinsapi.custom_exceptions import JenkinsAPIException


logger = logging.getLogger(__name__)

# Global Jenkins client instance
j: Optional[Jenkins] = None

# Environment variable names for Jenkins configuration
JENKINS_URL_VAR = "JENKINS_URL"
JENKINS_USER_VAR = "JENKINS_USER"
JENKINS_TOKEN_VAR = "JENKINS_TOKEN"


def initialize_jenkins_client() -> Optional[Jenkins]:
    """
    Initialize the Jenkins client with environment variables.
    
    Returns:
        Jenkins client instance or None if initialization fails
    """
    global j
    
    if j is not None:
        return j
    
    # Read environment variables at runtime
    jenkins_url = os.environ.get(JENKINS_URL_VAR)
    jenkins_user = os.environ.get(JENKINS_USER_VAR)
    jenkins_token = os.environ.get(JENKINS_TOKEN_VAR)
    
    if not all([jenkins_url, jenkins_user, jenkins_token]):
        logger.error("Jenkins credentials not configured in environment variables.")
        return None
    
    try:
        j = Jenkins(
            jenkins_url,
            username=jenkins_user,
            password=jenkins_token,
            timeout=30
        )
        logger.info(f"Jenkins client initialized successfully for {jenkins_url}")
        return j
    except JenkinsAPIException as e:
        logger.error(f"Failed to initialize Jenkins client: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Unexpected error during Jenkins client initialization: {e}", exc_info=True)
        return None


def get_jenkins_client() -> Optional[Jenkins]:
    """
    Get the global Jenkins client instance.
    Initializes the client if not already initialized.
    
    Returns:
        Jenkins client instance or None if initialization fails
    """
    global j
    
    if j is None:
        return initialize_jenkins_client()
    return j


def set_jenkins_client_for_testing(client: Jenkins):
    """
    Set the Jenkins client for testing purposes.
    
    Args:
        client: Jenkins client instance for testing
    """
    global j
    j = client


def is_jenkins_configured() -> bool:
    """
    Check if Jenkins credentials are configured.
    
    Returns:
        True if all required environment variables are set, False otherwise
    """
    return all([
        os.environ.get(JENKINS_URL_VAR),
        os.environ.get(JENKINS_USER_VAR),
        os.environ.get(JENKINS_TOKEN_VAR)
    ])


def get_jenkins_config() -> dict:
    """
    Get Jenkins configuration from environment variables.
    
    Returns:
        Dictionary containing Jenkins configuration
    """
    return {
        "url": os.environ.get(JENKINS_URL_VAR),
        "user": os.environ.get(JENKINS_USER_VAR),
        "token": os.environ.get(JENKINS_TOKEN_VAR)
    }


def check_jenkins_config() -> dict:
    """
    Check Jenkins configuration and return status.
    
    Returns:
        Dictionary with configuration status and details
    """
    config = get_jenkins_config()
    
    # Find missing variables
    missing_vars = []
    if not config["url"]:
        missing_vars.append("JENKINS_URL")
    if not config["user"]:
        missing_vars.append("JENKINS_USER")
    if not config["token"]:
        missing_vars.append("JENKINS_TOKEN")
    
    if missing_vars:
        return {
            "configured": False,
            "message": "Jenkins credentials not fully configured",
            "config": config,
            "missing_vars": missing_vars
        }
    
    return {
        "configured": True,
        "message": "Jenkins credentials configured",
        "config": config,
        "missing_vars": []
    }


def get_jenkins_env_vars() -> dict:
    """
    Get Jenkins environment variables with masked values for security.
    
    Returns:
        Dictionary with environment variable names and values (None for missing)
    """
    env_vars = {}
    
    # Always include all variables, set to None if missing
    env_vars["JENKINS_URL"] = os.environ.get(JENKINS_URL_VAR)
    env_vars["JENKINS_USER"] = os.environ.get(JENKINS_USER_VAR)
    
    jenkins_token = os.environ.get(JENKINS_TOKEN_VAR)
    if jenkins_token:
        # Mask the token for security
        env_vars["JENKINS_TOKEN"] = "***" + jenkins_token[-4:] if len(jenkins_token) > 4 else "***"
    else:
        env_vars["JENKINS_TOKEN"] = None
    
    return env_vars