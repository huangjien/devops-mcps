"""Azure authentication and credential management utilities."""

import logging
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

# Initialize Azure credentials
_credential = None


def get_azure_credential() -> DefaultAzureCredential:
  """Get Azure credential instance.

  Returns:
      DefaultAzureCredential: Azure credential instance for authentication.
  """
  global _credential
  if _credential is None:
    _credential = DefaultAzureCredential()
    logger.debug("Azure credential initialized")
  return _credential
