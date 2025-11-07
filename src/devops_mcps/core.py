"""DevOps MCP Server - Core module for integrating various DevOps tools.

This module provides MCP (Model Context Protocol) tools for interacting with:
- GitHub (repositories, issues, commits, etc.)
- Jenkins (jobs, builds, logs, etc.)
- Azure (subscriptions, VMs, AKS clusters, etc.)
- Artifactory (artifacts, repositories, etc.)

The server can be run with different transports (stdio, stream_http) and provides
both synchronous and asynchronous interfaces for various DevOps operations.

This module now serves as a compatibility layer, delegating to the new modular structure.
"""

import os
import sys
import logging

# Import main entry points from the new modular structure
from .main_entry import main, main_stream_http, setup_and_run
from .server_setup import create_mcp_server, initialize_clients
from .mcp_tools import register_tools
from .prompts import PromptLoader
from .prompt_management import load_and_register_prompts as _load_and_register_prompts
from .mcp_tools import (
  get_azure_subscriptions,
  list_azure_vms,
  list_aks_clusters,
  # GitHub tools
  search_repositories,
  github_get_current_user_info,
  get_file_contents,
  list_commits,
  list_issues,
  get_repository,
  search_code,
  get_github_issue_content,
  # Jenkins tools
  get_jenkins_jobs,
  get_jenkins_build_log,
  get_all_jenkins_views,
  get_recent_failed_jenkins_builds,
  # Artifactory tools
  list_artifactory_items,
  search_artifactory_items,
  get_artifactory_item_info,
  # Cache management
  clear_cache,
)
from . import github, jenkins, azure, artifactory

# Create logger and mcp instances for backward compatibility
logger = logging.getLogger(__name__)
mcp = create_mcp_server()

# Package version
package_version = "0.8.8"

# imports moved to top to satisfy Ruff E402


# Wrapper function for backward compatibility
def load_and_register_prompts():
  """Load and register prompts using the global mcp instance."""
  _load_and_register_prompts(mcp)


__all__ = [
  # Main entry points
  "main",
  "main_stream_http",
  "setup_and_run",
  # Server setup
  "create_mcp_server",
  "initialize_clients",
  # Tool registration
  "register_tools",
  # Prompt management
  "load_and_register_prompts",
  # For test compatibility
  "os",
  "sys",
  "logger",
  "mcp",
  # Module references
  "github",
  "jenkins",
  "azure",
  "artifactory",
  "PromptLoader",
  # Tool functions
  "get_azure_subscriptions",
  "list_azure_vms",
  "list_aks_clusters",
  "search_repositories",
  "github_get_current_user_info",
  "get_file_contents",
  "list_commits",
  "list_issues",
  "get_repository",
  "search_code",
  "get_github_issue_content",
  "get_jenkins_jobs",
  "get_jenkins_build_log",
  "get_all_jenkins_views",
  "get_recent_failed_jenkins_builds",
  "list_artifactory_items",
  "search_artifactory_items",
  "get_artifactory_item_info",
  "clear_cache",
]

# For backward compatibility, expose the main functions directly
if __name__ == "__main__":
  main()
