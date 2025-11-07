# /Users/huangjien/workspace/devops-mcps/src/devops_mcps/azure.py
"""Azure utilities for DevOps MCP server.

This module provides Azure-related functionality including:
- Subscription management
- Compute resource management
- Container management
- App Service management
- Authentication utilities

All functions are re-exported from their respective modules for backward compatibility."""

# Re-export functions from azure utils modules for backward compatibility
from .utils.azure.azure_subscriptions import get_subscriptions
from .utils.azure.azure_compute import list_virtual_machines
from .utils.azure.azure_containers import list_aks_clusters
from .utils.azure.azure_app_service import (
  list_app_services,
  get_app_service_details,
  get_app_service_metrics,
  list_app_service_plans,
)
from .utils.azure.azure_auth import get_azure_credential

__all__ = [
  "get_subscriptions",
  "list_virtual_machines",
  "list_aks_clusters",
  "list_app_services",
  "get_app_service_details",
  "get_app_service_metrics",
  "list_app_service_plans",
  "get_azure_credential",
]
