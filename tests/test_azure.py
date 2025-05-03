import pytest
from unittest.mock import Mock, patch
from azure.core.exceptions import AzureError
from azure.mgmt.subscription.models import Subscription
from azure.mgmt.compute.models import (
  VirtualMachine,
  HardwareProfile,
  StorageProfile,
  OSDisk,
)
from azure.mgmt.containerservice.models import ManagedCluster
from devops_mcps.azure import (
  get_subscriptions,
  list_virtual_machines,
  list_aks_clusters,
)


@pytest.fixture
def mock_subscription_client():
  with patch("devops_mcps.azure.SubscriptionClient") as mock_client:
    mock_instance = Mock()
    mock_client.return_value = mock_instance
    yield mock_instance


@pytest.fixture
def mock_compute_client():
  with patch("devops_mcps.azure.ComputeManagementClient") as mock_client:
    mock_instance = Mock()
    mock_client.return_value = mock_instance
    yield mock_instance


@pytest.fixture
def mock_container_client():
  with patch("devops_mcps.azure.ContainerServiceClient") as mock_client:
    mock_instance = Mock()
    mock_client.return_value = mock_instance
    yield mock_instance


def test_get_subscriptions_success(mock_subscription_client):
  # Arrange
  mock_sub = Mock(spec=Subscription)
  mock_sub.subscription_id = "test-sub-id"
  mock_sub.display_name = "Test Subscription"
  mock_sub.state = "Enabled"
  mock_sub.tenant_id = "test-tenant-id"
  mock_subscription_client.subscriptions.list.return_value = [mock_sub]

  # Act
  result = get_subscriptions()

  # Assert
  assert isinstance(result, list)
  assert len(result) == 1
  assert result[0]["subscription_id"] == "test-sub-id"
  assert result[0]["display_name"] == "Test Subscription"
  assert result[0]["state"] == "Enabled"
  assert result[0]["tenant_id"] == "test-tenant-id"


def test_get_subscriptions_error(mock_subscription_client):
  # Arrange
  mock_subscription_client.subscriptions.list.side_effect = AzureError("Test error")

  # Act
  result = get_subscriptions()

  # Assert
  assert isinstance(result, dict)
  assert "error" in result
  assert "Failed to get Azure subscriptions" in result["error"]


def test_list_virtual_machines_success(mock_compute_client):
  # Arrange
  mock_vm = Mock(spec=VirtualMachine)
  mock_vm.name = "test-vm"
  mock_vm.id = "/subscriptions/sub-id/resourceGroups/test-rg/providers/Microsoft.Compute/virtualMachines/test-vm"
  mock_vm.location = "eastus"
  mock_vm.hardware_profile = Mock(spec=HardwareProfile)
  mock_vm.hardware_profile.vm_size = "Standard_DS1_v2"
  mock_vm.storage_profile = Mock(spec=StorageProfile)
  mock_vm.storage_profile.os_disk = Mock(spec=OSDisk)
  mock_vm.storage_profile.os_disk.os_type = "Linux"
  mock_vm.provisioning_state = "Succeeded"

  mock_compute_client.virtual_machines.list_all.return_value = [mock_vm]

  # Act
  result = list_virtual_machines("test-sub-id")

  # Assert
  assert isinstance(result, list)
  assert len(result) == 1
  assert result[0]["name"] == "test-vm"
  assert result[0]["location"] == "eastus"
  assert result[0]["vm_size"] == "Standard_DS1_v2"
  assert result[0]["os_type"] == "Linux"
  assert result[0]["provisioning_state"] == "Succeeded"
  assert result[0]["resource_group"] == "test-rg"


def test_list_virtual_machines_error(mock_compute_client):
  # Arrange
  mock_compute_client.virtual_machines.list_all.side_effect = AzureError("Test error")

  # Act
  result = list_virtual_machines("test-sub-id")

  # Assert
  assert isinstance(result, dict)
  assert "error" in result
  assert "Failed to list virtual machines" in result["error"]


def test_list_aks_clusters_success(mock_container_client):
  # Arrange
  mock_cluster = Mock(spec=ManagedCluster)
  mock_cluster.name = "test-cluster"
  mock_cluster.id = "/subscriptions/sub-id/resourceGroups/test-rg/providers/Microsoft.ContainerService/managedClusters/test-cluster"
  mock_cluster.location = "eastus"
  mock_cluster.kubernetes_version = "1.24.0"
  mock_cluster.provisioning_state = "Succeeded"
  mock_cluster.fqdn = "test-cluster.azure.com"
  mock_cluster.node_resource_group = "MC_test-rg_test-cluster_eastus"

  mock_container_client.managed_clusters.list.return_value = [mock_cluster]

  # Act
  result = list_aks_clusters("test-sub-id")

  # Assert
  assert isinstance(result, list)
  assert len(result) == 1
  assert result[0]["name"] == "test-cluster"
  assert result[0]["location"] == "eastus"
  assert result[0]["kubernetes_version"] == "1.24.0"
  assert result[0]["provisioning_state"] == "Succeeded"
  assert result[0]["fqdn"] == "test-cluster.azure.com"
  assert result[0]["resource_group"] == "test-rg"
  assert result[0]["node_resource_group"] == "MC_test-rg_test-cluster_eastus"


def test_list_aks_clusters_error(mock_container_client):
  # Arrange
  mock_container_client.managed_clusters.list.side_effect = AzureError("Test error")

  # Act
  result = list_aks_clusters("test-sub-id")

  # Assert
  assert isinstance(result, dict)
  assert "error" in result
  assert "Failed to list AKS clusters" in result["error"]
