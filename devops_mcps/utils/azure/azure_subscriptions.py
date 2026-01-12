"""Azure subscription management utilities."""

import logging
from typing import Dict, List, Any, Union
from azure.mgmt.subscription import SubscriptionClient
from .azure_auth import get_azure_credential

logger = logging.getLogger(__name__)


def get_subscriptions() -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Get list of Azure subscriptions.

  Returns:
      List of subscription dictionaries or an error dictionary.
  """
  try:
    credential = get_azure_credential()
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
