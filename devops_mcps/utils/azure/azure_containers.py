"""Azure container service management utilities."""

import logging
from typing import Dict, List, Any, Union
from azure.mgmt.containerservice import ContainerServiceClient
from .azure_auth import get_azure_credential

logger = logging.getLogger(__name__)


def list_aks_clusters(
  subscription_id: str,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """List all AKS clusters in a subscription.

  Args:
      subscription_id: Azure subscription ID.

  Returns:
      List of AKS cluster dictionaries or an error dictionary.
  """
  try:
    credential = get_azure_credential()
    container_client = ContainerServiceClient(credential, subscription_id)
    clusters = []
    for cluster in container_client.managed_clusters.list():
      clusters.append(
        {
          "name": cluster.name,
          "id": cluster.id,
          "location": cluster.location,
          "kubernetes_version": cluster.kubernetes_version,
          "provisioning_state": cluster.provisioning_state,
          "fqdn": cluster.fqdn,
          "resource_group": cluster.id.split("/")[4],
          "node_resource_group": cluster.node_resource_group,
        }
      )
    return clusters
  except Exception as e:
    logger.error(
      f"Error listing AKS clusters for subscription {subscription_id}: {str(e)}"
    )
    return {"error": f"Failed to list AKS clusters: {str(e)}"}
