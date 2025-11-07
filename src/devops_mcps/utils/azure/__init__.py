"""Azure utility modules for DevOps MCP Server.

This package contains utility modules for Azure operations:
- azure_auth: Authentication and credential management
- azure_compute: Virtual machine management
- azure_containers: Container and AKS management
- azure_app_service: App Service and App Service Plan management
- azure_subscriptions: Subscription management
"""

from .azure_auth import get_azure_credential
from .azure_compute import list_virtual_machines
from .azure_containers import (
  list_aks_clusters,
)
from .azure_app_service import (
  list_app_services,
  get_app_service_details,
  get_app_service_metrics,
  list_app_service_plans,
)
from .azure_subscriptions import get_subscriptions

__all__ = [
  "get_azure_credential",
  "list_virtual_machines",
  "list_aks_clusters",
  "list_app_services",
  "get_app_service_details",
  "get_app_service_metrics",
  "list_app_service_plans",
  "get_subscriptions",
]
