# /Users/huangjien/workspace/devops-mcps/src/devops_mcps/azure.py
"""Azure management module for DevOps MCP Server.

This module provides a unified interface for Azure operations by importing
functions from specialized utility modules.
"""

# Import functions from utility modules
from .utils.azure.azure_subscriptions import get_subscriptions
from .utils.azure.azure_compute import list_virtual_machines
from .utils.azure.azure_containers import list_aks_clusters
from .utils.azure.azure_auth import get_azure_credential

# Re-export all functions for backward compatibility
__all__ = [
    "get_subscriptions",
    "list_virtual_machines",
    "list_aks_clusters",
    "get_azure_credential",
]
