"""Jenkins client initialization and authentication utilities."""

import logging
import os
import sys
from typing import Optional

# Third-party imports
from jenkinsapi.jenkins import Jenkins, JenkinsAPIException
from requests.exceptions import ConnectionError

logger = logging.getLogger(__name__)

# --- Jenkins Client Configuration ---
# Note: Environment variables are read in initialize_jenkins_client() to ensure
# load_dotenv() is called first in server_setup.py
JENKINS_URL = None
JENKINS_USER = None
JENKINS_TOKEN = None
LOG_LENGTH = None
j: Optional[Jenkins] = None

# Export constants and functions
__all__ = [
  "JENKINS_URL",
  "JENKINS_USER",
  "JENKINS_TOKEN",
  "LOG_LENGTH",
  "j",
  "initialize_jenkins_client",
  "set_jenkins_client_for_testing",
]


def initialize_jenkins_client():
  """Initializes the global Jenkins client 'j'."""
  global j, JENKINS_URL, JENKINS_USER, JENKINS_TOKEN, LOG_LENGTH
  if j:  # Already initialized
    return j

  # Read environment variables (after load_dotenv() has been called)
  JENKINS_URL = os.environ.get("JENKINS_URL")
  JENKINS_USER = os.environ.get("JENKINS_USER")
  JENKINS_TOKEN = os.environ.get("JENKINS_TOKEN")
  LOG_LENGTH = os.environ.get("LOG_LENGTH", 10240)  # Default to 10KB if not set

  if JENKINS_URL and JENKINS_USER and JENKINS_TOKEN:
    try:
      j = Jenkins(JENKINS_URL, username=JENKINS_USER, password=JENKINS_TOKEN)
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
