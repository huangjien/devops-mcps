"""Azure compute management utilities."""

import logging
from typing import Dict, List, Any, Union
from azure.mgmt.compute import ComputeManagementClient
from .azure_auth import get_azure_credential

logger = logging.getLogger(__name__)


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
    credential = get_azure_credential()
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
