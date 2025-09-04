"""Azure utility modules for DevOps MCP Server.

This package contains utility modules for Azure operations:
- azure_auth: Authentication and credential management
- azure_compute: Virtual machine management
- azure_containers: AKS cluster management
- azure_subscriptions: Subscription management
"""

from .azure_auth import get_azure_credential
from .azure_compute import list_virtual_machines
from .azure_containers import list_aks_clusters
from .azure_subscriptions import get_subscriptions

__all__ = [
    "get_azure_credential",
    "list_virtual_machines",
    "list_aks_clusters",
    "get_subscriptions",
]