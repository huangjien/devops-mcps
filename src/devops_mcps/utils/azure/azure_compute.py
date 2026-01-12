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
      vm_id = vm.id or ""
      hardware_profile = getattr(vm, "hardware_profile", None)
      storage_profile = getattr(vm, "storage_profile", None)
      os_disk = getattr(storage_profile, "os_disk", None) if storage_profile else None
      vms.append(
        {
          "name": vm.name,
          "id": vm.id,
          "location": vm.location,
          "vm_size": getattr(hardware_profile, "vm_size", None),
          "os_type": getattr(os_disk, "os_type", None),
          "provisioning_state": vm.provisioning_state,
          "resource_group": vm_id.split("/")[4] if vm_id else "",
        }
      )
    return vms
  except Exception as e:
    logger.error(f"Error listing VMs for subscription {subscription_id}: {str(e)}")
    return {"error": f"Failed to list virtual machines: {str(e)}"}
