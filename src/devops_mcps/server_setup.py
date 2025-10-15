"""Server setup module for FastMCP initialization and configuration.

This module handles the initialization of the FastMCP server, environment setup,
package version detection, and logging configuration.
"""

import logging
import os
from dotenv import load_dotenv
from importlib.metadata import version, PackageNotFoundError
from mcp.server.fastmcp import FastMCP

from .logger import setup_logging

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def get_package_version() -> str:
  """Get the package version using importlib.metadata.

  Returns:
      str: Package version string or fallback if not found
  """
  try:
    package_version = version("devops-mcps")
    logger.info(f"Loaded package version: {package_version}")
    return package_version
  except PackageNotFoundError:
    logger.warning(
      "Could not determine package version using importlib.metadata. "
      "Is the package installed correctly? Falling back to 'unknown'."
    )
    return "?.?.?"  # Provide a fallback


def create_mcp_server() -> FastMCP:
  """Create and configure the FastMCP server instance.

  Returns:
      FastMCP: Configured FastMCP server instance
  """
  package_version = get_package_version()
  mcp = FastMCP(f"DevOps MCP Server v{package_version} (Github & Jenkins)")
  logger.info(f"Created FastMCP server with version {package_version}")
  return mcp


def initialize_clients():
  """Initialize and validate external service clients.

  This function initializes GitHub and Jenkins clients and validates
  their configuration, logging appropriate warnings or errors.
  """
  from . import github, jenkins
  from .utils.github import github_client
  import sys

  # Initialize GitHub client
  github.initialize_github_client(force=True)

  # Check if the GitHub client initialized successfully
  if github_client.g is None:
    # Check the environment variable directly instead of the cached value
    current_github_token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
    if current_github_token:
      logger.error(
        "GitHub client failed to initialize despite token being present. Check logs. Exiting."
      )
      sys.exit(1)
    else:
      # Allow running without auth, but tools will return errors if called
      logger.warning(
        "Running without GitHub authentication. GitHub tools will fail if used."
      )

  # Check if the Jenkins client initialized successfully
  if jenkins.j is None:
    if jenkins.JENKINS_URL and jenkins.JENKINS_USER and jenkins.JENKINS_TOKEN:
      logger.error(
        "Jenkins client failed to initialize despite credentials being present. Check logs. Exiting."
      )
      sys.exit(1)
    else:
      logger.warning(
        "Running without Jenkins authentication. Jenkins tools will fail if used."
      )
