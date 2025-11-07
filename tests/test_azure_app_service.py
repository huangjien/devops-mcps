"""Tests for Azure App Service utilities."""

from unittest.mock import Mock, patch

from devops_mcps.utils.azure.azure_app_service import (
  list_app_services,
  get_app_service_details,
  get_app_service_metrics,
  list_app_service_plans,
)


class TestAzureAppService:
  """Test cases for Azure App Service utilities."""

  @patch("devops_mcps.utils.azure.azure_app_service.get_azure_credential")
  @patch("devops_mcps.utils.azure.azure_app_service.WebSiteManagementClient")
  def test_list_app_services_success(self, mock_web_client_class, mock_get_credential):
    """Test successful listing of App Services."""
    # Setup mocks
    mock_credential = Mock()
    mock_get_credential.return_value = mock_credential

    mock_web_client = Mock()
    mock_web_client_class.return_value = mock_web_client

    # Mock App Service data
    mock_site = Mock()
    mock_site.name = "test-app"
    mock_site.id = "/subscriptions/test-sub/resourceGroups/test-rg/providers/Microsoft.Web/sites/test-app"
    mock_site.location = "East US"
    mock_site.resource_group = "test-rg"
    mock_site.state = "Running"
    mock_site.enabled = True
    mock_site.default_host_name = "test-app.azurewebsites.net"
    mock_site.kind = "app"
    mock_site.server_farm_id = "/subscriptions/test-sub/resourceGroups/test-rg/providers/Microsoft.Web/serverfarms/test-plan"
    mock_site.https_only = True
    mock_site.client_affinity_enabled = False
    mock_site.tags = {"environment": "test"}

    mock_web_client.web_apps.list.return_value = [mock_site]

    # Mock configuration
    mock_config = Mock()
    mock_config.net_framework_version = "v4.0"
    mock_config.php_version = ""
    mock_config.python_version = "3.9"
    mock_config.node_version = ""
    mock_config.java_version = ""
    mock_config.linux_fx_version = "PYTHON|3.9"
    mock_config.windows_fx_version = ""
    mock_web_client.web_apps.get_configuration.return_value = mock_config

    # Execute
    result = list_app_services("test-subscription-id")

    # Verify
    assert isinstance(result, list)
    assert len(result) == 1

    app_service = result[0]
    assert app_service["name"] == "test-app"
    assert app_service["location"] == "East US"
    assert app_service["state"] == "Running"
    assert app_service["enabled"] is True
    assert app_service["runtime"]["python_version"] == "3.9"

    # Verify client calls
    mock_web_client_class.assert_called_once_with(
      mock_credential, "test-subscription-id"
    )
    mock_web_client.web_apps.list.assert_called_once()

  @patch("devops_mcps.utils.azure.azure_app_service.get_azure_credential")
  @patch("devops_mcps.utils.azure.azure_app_service.WebSiteManagementClient")
  def test_list_app_services_by_resource_group(
    self, mock_web_client_class, mock_get_credential
  ):
    """Test listing App Services filtered by resource group."""
    # Setup mocks
    mock_credential = Mock()
    mock_get_credential.return_value = mock_credential

    mock_web_client = Mock()
    mock_web_client_class.return_value = mock_web_client
    mock_web_client.web_apps.list_by_resource_group.return_value = []

    # Execute
    result = list_app_services("test-subscription-id", "test-rg")

    # Verify
    assert isinstance(result, list)
    mock_web_client.web_apps.list_by_resource_group.assert_called_once_with("test-rg")

  @patch("devops_mcps.utils.azure.azure_app_service.get_azure_credential")
  def test_list_app_services_auth_error(self, mock_get_credential):
    """Test handling of authentication errors."""
    mock_get_credential.side_effect = Exception("Authentication failed")

    result = list_app_services("test-subscription-id")

    assert isinstance(result, dict)
    assert "error" in result
    assert "Authentication failed" in result["error"]

  @patch("devops_mcps.utils.azure.azure_app_service.get_azure_credential")
  @patch("devops_mcps.utils.azure.azure_app_service.WebSiteManagementClient")
  def test_get_app_service_details_success(
    self, mock_web_client_class, mock_get_credential
  ):
    """Test successful retrieval of App Service details."""
    # Setup mocks
    mock_credential = Mock()
    mock_get_credential.return_value = mock_credential

    mock_web_client = Mock()
    mock_web_client_class.return_value = mock_web_client

    # Mock App Service data
    mock_site = Mock()
    mock_site.name = "test-app"
    mock_site.id = "/subscriptions/test-sub/resourceGroups/test-rg/providers/Microsoft.Web/sites/test-app"
    mock_site.location = "East US"
    mock_site.resource_group = "test-rg"
    mock_site.state = "Running"
    mock_site.enabled = True
    mock_site.default_host_name = "test-app.azurewebsites.net"
    mock_site.kind = "app"
    mock_site.https_only = True
    mock_site.client_affinity_enabled = False
    mock_site.tags = {"environment": "test"}
    mock_site.outbound_ip_addresses = "1.2.3.4,5.6.7.8"
    mock_site.possible_outbound_ip_addresses = "1.2.3.4,5.6.7.8,9.10.11.12"

    mock_web_client.web_apps.get.return_value = mock_site

    # Mock configuration
    mock_config = Mock()
    mock_config.always_on = True
    mock_config.http20_enabled = True
    mock_config.ftps_state = "FtpsOnly"
    mock_config.min_tls_version = "1.2"
    mock_web_client.web_apps.get_configuration.return_value = mock_config

    # Mock application settings
    mock_app_settings = Mock()
    mock_app_settings.properties = {
      "WEBSITE_NODE_DEFAULT_VERSION": "14.15.0",
      "DATABASE_CONNECTION_STRING": "secret-value",
      "API_KEY": "secret-key",
    }
    mock_web_client.web_apps.list_application_settings.return_value = mock_app_settings

    # Mock deployment slots
    mock_slot = Mock()
    mock_slot.name = "test-app/staging"
    mock_slot.state = "Running"
    mock_slot.enabled = True
    mock_slot.default_host_name = "test-app-staging.azurewebsites.net"
    mock_web_client.web_apps.list_slots.return_value = [mock_slot]

    # Execute
    result = get_app_service_details("test-subscription-id", "test-rg", "test-app")

    # Verify
    assert isinstance(result, dict)
    assert result["name"] == "test-app"
    assert result["state"] == "Running"
    assert result["configuration"]["always_on"] is True
    assert result["application_settings"]["WEBSITE_NODE_DEFAULT_VERSION"] == "14.15.0"
    assert result["application_settings"]["DATABASE_CONNECTION_STRING"] == "[HIDDEN]"
    assert result["application_settings"]["API_KEY"] == "[HIDDEN]"
    assert len(result["deployment_slots"]) == 1
    assert result["deployment_slots"][0]["name"] == "test-app/staging"

  @patch("devops_mcps.utils.azure.azure_app_service.get_azure_credential")
  @patch("devops_mcps.utils.azure.azure_app_service.WebSiteManagementClient")
  def test_get_app_service_metrics_success(
    self, mock_web_client_class, mock_get_credential
  ):
    """Test successful retrieval of App Service metrics."""
    # Setup mocks
    mock_credential = Mock()
    mock_get_credential.return_value = mock_credential

    mock_web_client = Mock()
    mock_web_client_class.return_value = mock_web_client

    # Mock App Service data
    mock_site = Mock()
    mock_site.state = "Running"
    mock_site.enabled = True
    mock_site.usage_state = "Normal"
    mock_web_client.web_apps.get.return_value = mock_site

    # Mock usage metrics
    mock_usage = Mock()
    mock_usage.name = Mock()
    mock_usage.name.value = "CpuTime"
    mock_usage.current_value = 120.5
    mock_usage.limit = 1000.0
    mock_usage.unit = "Seconds"
    mock_web_client.web_apps.list_usages.return_value = [mock_usage]

    # Execute
    result = get_app_service_metrics(
      "test-subscription-id", "test-rg", "test-app", "PT24H"
    )

    # Verify
    assert isinstance(result, dict)
    assert result["app_name"] == "test-app"
    assert result["time_range"] == "PT24H"
    assert result["state"] == "Running"
    assert len(result["resource_usage"]) == 1
    assert result["resource_usage"][0]["name"] == "CpuTime"
    assert result["resource_usage"][0]["current_value"] == 120.5

  @patch("devops_mcps.utils.azure.azure_app_service.get_azure_credential")
  @patch("devops_mcps.utils.azure.azure_app_service.WebSiteManagementClient")
  def test_list_app_service_plans_success(
    self, mock_web_client_class, mock_get_credential
  ):
    """Test successful listing of App Service Plans."""
    # Setup mocks
    mock_credential = Mock()
    mock_get_credential.return_value = mock_credential

    mock_web_client = Mock()
    mock_web_client_class.return_value = mock_web_client

    # Mock App Service Plan data
    mock_plan = Mock()
    mock_plan.name = "test-plan"
    mock_plan.id = "/subscriptions/test-sub/resourceGroups/test-rg/providers/Microsoft.Web/serverfarms/test-plan"
    mock_plan.location = "East US"
    mock_plan.resource_group = "test-rg"
    mock_plan.kind = "app"
    mock_plan.sku = Mock()
    mock_plan.sku.name = "S1"
    mock_plan.sku.tier = "Standard"
    mock_plan.sku.size = "S1"
    mock_plan.sku.capacity = 1
    mock_plan.status = "Ready"
    mock_plan.number_of_sites = 2
    mock_plan.maximum_number_of_workers = 3
    mock_plan.per_site_scaling = False
    mock_plan.is_spot = False
    mock_plan.tags = {"environment": "production"}

    mock_web_client.app_service_plans.list.return_value = [mock_plan]

    # Execute
    result = list_app_service_plans("test-subscription-id")

    # Verify
    assert isinstance(result, list)
    assert len(result) == 1

    plan = result[0]
    assert plan["name"] == "test-plan"
    assert plan["sku"]["name"] == "S1"
    assert plan["sku"]["tier"] == "Standard"
    assert plan["number_of_sites"] == 2
    assert plan["is_spot"] is False

  def test_error_handling_empty_parameters(self):
    """Test error handling for empty parameters."""
    # Test empty subscription_id
    result = list_app_services("")
    assert isinstance(result, dict)
    assert "error" in result

    result = get_app_service_details("", "test-rg", "test-app")
    assert isinstance(result, dict)
    assert "error" in result

    result = get_app_service_details("test-sub", "", "test-app")
    assert isinstance(result, dict)
    assert "error" in result

    result = get_app_service_details("test-sub", "test-rg", "")
    assert isinstance(result, dict)
    assert "error" in result

  @patch("devops_mcps.utils.azure.azure_app_service.get_azure_credential")
  @patch("devops_mcps.utils.azure.azure_app_service.WebSiteManagementClient")
  def test_configuration_access_error(self, mock_web_client_class, mock_get_credential):
    """Test handling of configuration access errors."""
    # Setup mocks
    mock_credential = Mock()
    mock_get_credential.return_value = mock_credential

    mock_web_client = Mock()
    mock_web_client_class.return_value = mock_web_client

    # Mock App Service data
    mock_site = Mock()
    mock_site.name = "test-app"
    mock_site.resource_group = "test-rg"
    mock_site.id = "/subscriptions/test-sub/resourceGroups/test-rg/providers/Microsoft.Web/sites/test-app"
    mock_site.location = "East US"
    mock_site.state = "Running"
    mock_site.enabled = True
    mock_site.default_host_name = "test-app.azurewebsites.net"
    mock_site.kind = "app"
    mock_site.server_farm_id = "/subscriptions/test-sub/resourceGroups/test-rg/providers/Microsoft.Web/serverfarms/test-plan"
    mock_site.https_only = True
    mock_site.client_affinity_enabled = False
    mock_site.tags = {}
    mock_web_client.web_apps.list.return_value = [mock_site]

    # Mock configuration error
    mock_web_client.web_apps.get_configuration.side_effect = Exception("Access denied")

    # Execute
    result = list_app_services("test-subscription-id")

    # Verify
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["runtime"]["error"] == "Configuration not accessible"