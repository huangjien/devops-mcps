"""Jenkins client initialization and authentication utilities."""

import logging
import os
import sys
from typing import Optional

# Third-party imports
from jenkinsapi.jenkins import Jenkins, JenkinsAPIException
from requests.exceptions import ConnectionError

logger = logging.getLogger(__name__)

# Global variables
LOG_LENGTH = os.environ.get("LOG_LENGTH", 10240)  # Default to 10KB if not set
j: Optional[Jenkins] = None


def initialize_jenkins_client():
    """Initializes the global Jenkins client 'j'."""
    global j
    if j:  # Already initialized
        return j

    # Read environment variables dynamically to support testing
    jenkins_url = os.environ.get("JENKINS_URL")
    jenkins_user = os.environ.get("JENKINS_USER")
    jenkins_token = os.environ.get("JENKINS_TOKEN")

    if jenkins_url and jenkins_user and jenkins_token:
        try:
            j = Jenkins(jenkins_url, username=jenkins_user, password=jenkins_token)
            # Basic connection test
            _ = j.get_master_data()
            logger.info(
                "Successfully authenticated with Jenkins using JENKINS_URL, JENKINS_USER and JENKINS_TOKEN."
            )
        except JenkinsAPIException as e:
            logger.error(f"Failed to initialize authenticated Jenkins client: {e}")
            j = None
        except ConnectionError as e:
            logger.error(f"Failed to connect to Jenkins server: {e}")
            j = None
        except Exception as e:
            logger.error(f"Unexpected error initializing authenticated Jenkins client: {e}")
            j = None
    else:
        logger.warning(
            "JENKINS_URL, JENKINS_USER, or JENKINS_TOKEN environment variable not set."
        )
        logger.warning("Jenkins related tools will have limited functionality.")
        j = None
    return j


def set_jenkins_client_for_testing(client):
    """Set Jenkins client for testing purposes."""
    global j
    j = client


# Call initialization when the module is loaded
if not any("pytest" in arg or "unittest" in arg for arg in sys.argv):
    initialize_jenkins_client()