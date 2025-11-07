"""Azure App Service management utilities."""

import logging
from typing import Dict, List, Any, Union, Optional
from azure.mgmt.web import WebSiteManagementClient
from .azure_auth import get_azure_credential

logger = logging.getLogger(__name__)


def list_app_services(
  subscription_id: str,
  resource_group: Optional[str] = None,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """List all App Services in a subscription or resource group.

  Args:
      subscription_id: Azure subscription ID.
      resource_group: Optional resource group name to filter results.

  Returns:
      List of App Service dictionaries or an error dictionary.
  """
  try:
    credential = get_azure_credential()
    web_client = WebSiteManagementClient(credential, subscription_id)

    app_services = []

    if resource_group:
      # List App Services in specific resource group
      sites = web_client.web_apps.list_by_resource_group(resource_group)
    else:
      # List all App Services in subscription
      sites = web_client.web_apps.list()

    for site in sites:
      app_service_info = {
        "name": site.name,
        "id": site.id,
        "location": site.location,
        "resource_group": site.resource_group,
        "state": site.state,
        "enabled": site.enabled,
        "default_host_name": site.default_host_name,
        "kind": site.kind,
        "sku": {
          "name": site.server_farm_id.split("/")[-1] if site.server_farm_id else None,
          "tier": getattr(site, "sku", {}).get("tier")
          if hasattr(site, "sku")
          else None,
        },
        "https_only": site.https_only,
        "client_affinity_enabled": site.client_affinity_enabled,
        "tags": site.tags or {},
      }

      # Add runtime information if available
      try:
        config = web_client.web_apps.get_configuration(site.resource_group, site.name)
        app_service_info["runtime"] = {
          "net_framework_version": config.net_framework_version,
          "php_version": config.php_version,
          "python_version": config.python_version,
          "node_version": config.node_version,
          "java_version": config.java_version,
          "linux_fx_version": config.linux_fx_version,
          "windows_fx_version": config.windows_fx_version,
        }
      except Exception as config_error:
        logger.warning(f"Could not get configuration for {site.name}: {config_error}")
        app_service_info["runtime"] = {"error": "Configuration not accessible"}

      app_services.append(app_service_info)

    return app_services

  except Exception as e:
    error_msg = f"Error listing App Services for subscription {subscription_id}"
    if resource_group:
      error_msg += f" in resource group {resource_group}"
    error_msg += f": {str(e)}"
    logger.error(error_msg)
    return {"error": f"Failed to list App Services: {str(e)}"}


def get_app_service_details(
  subscription_id: str,
  resource_group: str,
  app_name: str,
) -> Union[Dict[str, Any], Dict[str, str]]:
  """Get detailed information about a specific App Service.

  Args:
      subscription_id: Azure subscription ID.
      resource_group: Resource group name.
      app_name: App Service name.

  Returns:
      App Service details dictionary or an error dictionary.
  """
  try:
    credential = get_azure_credential()
    web_client = WebSiteManagementClient(credential, subscription_id)

    # Get basic App Service information
    site = web_client.web_apps.get(resource_group, app_name)

    app_details = {
      "name": site.name,
      "id": site.id,
      "location": site.location,
      "resource_group": site.resource_group,
      "state": site.state,
      "enabled": site.enabled,
      "default_host_name": site.default_host_name,
      "kind": site.kind,
      "https_only": site.https_only,
      "client_affinity_enabled": site.client_affinity_enabled,
      "tags": site.tags or {},
      "outbound_ip_addresses": site.outbound_ip_addresses,
      "possible_outbound_ip_addresses": site.possible_outbound_ip_addresses,
    }

    # Get configuration details
    try:
      config = web_client.web_apps.get_configuration(resource_group, app_name)
      app_details["configuration"] = {
        "net_framework_version": config.net_framework_version,
        "php_version": config.php_version,
        "python_version": config.python_version,
        "node_version": config.node_version,
        "java_version": config.java_version,
        "linux_fx_version": config.linux_fx_version,
        "windows_fx_version": config.windows_fx_version,
        "always_on": config.always_on,
        "http20_enabled": config.http20_enabled,
        "ftps_state": config.ftps_state,
        "min_tls_version": config.min_tls_version,
      }
    except Exception as config_error:
      logger.warning(f"Could not get configuration for {app_name}: {config_error}")
      app_details["configuration"] = {"error": "Configuration not accessible"}

    # Get application settings (without sensitive values)
    try:
      app_settings = web_client.web_apps.list_application_settings(
        resource_group, app_name
      )
      # Only include non-sensitive setting names
      safe_settings = {}
      for key, value in app_settings.properties.items():
        if any(
          sensitive in key.lower()
          for sensitive in ["password", "secret", "key", "token", "connection"]
        ):
          safe_settings[key] = "[HIDDEN]"
        else:
          safe_settings[key] = value
      app_details["application_settings"] = safe_settings
    except Exception as settings_error:
      logger.warning(
        f"Could not get application settings for {app_name}: {settings_error}"
      )
      app_details["application_settings"] = {
        "error": "Application settings not accessible"
      }

    # Get deployment slots
    try:
      slots = list(web_client.web_apps.list_slots(resource_group, app_name))
      app_details["deployment_slots"] = [
        {
          "name": slot.name,
          "state": slot.state,
          "enabled": slot.enabled,
          "default_host_name": slot.default_host_name,
        }
        for slot in slots
      ]
    except Exception as slots_error:
      logger.warning(f"Could not get deployment slots for {app_name}: {slots_error}")
      app_details["deployment_slots"] = []

    return app_details

  except Exception as e:
    error_msg = f"Error getting details for App Service {app_name} in resource group {resource_group}: {str(e)}"
    logger.error(error_msg)
    return {"error": f"Failed to get App Service details: {str(e)}"}


def get_app_service_metrics(
  subscription_id: str,
  resource_group: str,
  app_name: str,
  time_range: str = "PT1H",  # Last 1 hour by default
) -> Union[Dict[str, Any], Dict[str, str]]:
  """Get metrics for a specific App Service.

  Args:
      subscription_id: Azure subscription ID.
      resource_group: Resource group name.
      app_name: App Service name.
      time_range: Time range for metrics (ISO 8601 duration format).

  Returns:
      App Service metrics dictionary or an error dictionary.
  """
  try:
    credential = get_azure_credential()
    web_client = WebSiteManagementClient(credential, subscription_id)

    # Get basic metrics from the App Service
    site = web_client.web_apps.get(resource_group, app_name)

    metrics_info = {
      "app_name": app_name,
      "resource_group": resource_group,
      "time_range": time_range,
      "state": site.state,
      "enabled": site.enabled,
      "usage_state": site.usage_state,
    }

    # Note: For detailed metrics like CPU, memory, requests, etc.,
    # you would typically use Azure Monitor API (azure-mgmt-monitor)
    # This is a simplified version showing basic status information

    try:
      # Get usage metrics if available
      usages = list(web_client.web_apps.list_usages(resource_group, app_name))
      metrics_info["resource_usage"] = [
        {
          "name": usage.name.value if usage.name else "Unknown",
          "current_value": usage.current_value,
          "limit": usage.limit,
          "unit": usage.unit,
        }
        for usage in usages
      ]
    except Exception as usage_error:
      logger.warning(f"Could not get usage metrics for {app_name}: {usage_error}")
      metrics_info["resource_usage"] = []

    return metrics_info

  except Exception as e:
    error_msg = f"Error getting metrics for App Service {app_name}: {str(e)}"
    logger.error(error_msg)
    return {"error": f"Failed to get App Service metrics: {str(e)}"}


def list_app_service_plans(
  subscription_id: str,
  resource_group: Optional[str] = None,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """List all App Service Plans in a subscription or resource group.

  Args:
      subscription_id: Azure subscription ID.
      resource_group: Optional resource group name to filter results.

  Returns:
      List of App Service Plan dictionaries or an error dictionary.
  """
  try:
    credential = get_azure_credential()
    web_client = WebSiteManagementClient(credential, subscription_id)

    app_service_plans = []

    if resource_group:
      # List App Service Plans in specific resource group
      plans = web_client.app_service_plans.list_by_resource_group(resource_group)
    else:
      # List all App Service Plans in subscription
      plans = web_client.app_service_plans.list()

    for plan in plans:
      plan_info = {
        "name": plan.name,
        "id": plan.id,
        "location": plan.location,
        "resource_group": plan.resource_group,
        "kind": plan.kind,
        "sku": {
          "name": plan.sku.name if plan.sku else None,
          "tier": plan.sku.tier if plan.sku else None,
          "size": plan.sku.size if plan.sku else None,
          "capacity": plan.sku.capacity if plan.sku else None,
        },
        "status": plan.status,
        "number_of_sites": plan.number_of_sites,
        "maximum_number_of_workers": plan.maximum_number_of_workers,
        "per_site_scaling": plan.per_site_scaling,
        "is_spot": plan.is_spot,
        "tags": plan.tags or {},
      }

      app_service_plans.append(plan_info)

    return app_service_plans

  except Exception as e:
    error_msg = f"Error listing App Service Plans for subscription {subscription_id}"
    if resource_group:
      error_msg += f" in resource group {resource_group}"
    error_msg += f": {str(e)}"
    logger.error(error_msg)
    return {"error": f"Failed to list App Service Plans: {str(e)}"}