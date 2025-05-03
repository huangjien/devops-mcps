# /Users/huangjien/workspace/devops-mcps/src/devops_mcps/azure.py
import logging
from typing import Dict, List, Any, Union
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.containerservice import ContainerServiceClient
from azure.mgmt.subscription import SubscriptionClient

logger = logging.getLogger(__name__)

# Initialize Azure credentials
credential = DefaultAzureCredential()


def get_subscriptions() -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Get list of Azure subscriptions.

  Returns:
      List of subscription dictionaries or an error dictionary.
  """
  try:
    subscription_client = SubscriptionClient(credential)
    subscriptions = []
    for sub in subscription_client.subscriptions.list():
      subscriptions.append(
        {
          "subscription_id": sub.subscription_id,
          "display_name": sub.display_name,
          "state": sub.state,
          "tenant_id": sub.tenant_id,
        }
      )
    return subscriptions
  except Exception as e:
    logger.error(f"Error getting Azure subscriptions: {str(e)}")
    return {"error": f"Failed to get Azure subscriptions: {str(e)}"}


def list_virtual_machines(
  subscription_id: str,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """List all virtual machines in a subscription.

  Args:
      subscription_id: Azure subscription ID.

  Returns:
      List of VM dictionaries or an error dictionary.
  """
  try:
    compute_client = ComputeManagementClient(credential, subscription_id)
    vms = []
    for vm in compute_client.virtual_machines.list_all():
      vms.append(
        {
          "name": vm.name,
          "id": vm.id,
          "location": vm.location,
          "vm_size": vm.hardware_profile.vm_size,
          "os_type": vm.storage_profile.os_disk.os_type,
          "provisioning_state": vm.provisioning_state,
          "resource_group": vm.id.split("/")[4],
        }
      )
    return vms
  except Exception as e:
    logger.error(f"Error listing VMs for subscription {subscription_id}: {str(e)}")
    return {"error": f"Failed to list virtual machines: {str(e)}"}


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
