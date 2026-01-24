"""Fetch a minimal Azure snapshot using env/.env service principal credentials."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv


def _get_env(name: str) -> str:
  return os.environ.get(name, "").strip()


def _load_dotenv_if_enabled() -> None:
  if os.environ.get("DEVOPS_MCPS_SKILL_IGNORE_DOTENV", "").strip().lower() in {
    "1",
    "true",
    "yes",
  }:
    return
  load_dotenv()


def get_snapshot(max_subscriptions: int = 25) -> dict[str, Any]:
  """Return minimal Azure subscription information."""
  _load_dotenv_if_enabled()

  client_id = _get_env("AZURE_CLIENT_ID")
  client_secret = _get_env("AZURE_CLIENT_SECRET")
  tenant_id = _get_env("AZURE_TENANT_ID")

  missing = [
    n
    for n, v in [
      ("AZURE_CLIENT_ID", client_id),
      ("AZURE_CLIENT_SECRET", client_secret),
      ("AZURE_TENANT_ID", tenant_id),
    ]
    if not v
  ]
  if missing:
    return {
      "skipped": True,
      "reason": (
        "Azure service principal credentials are not configured via env/.env. "
        "Azure CLI or managed identity authentication is not detected by this script."
      ),
      "missing_env": missing,
    }

  try:
    from azure.identity import DefaultAzureCredential
    from azure.mgmt.subscription import SubscriptionClient
  except Exception as exc:
    return {
      "status": "error",
      "error": f"Azure SDK import failed: {type(exc).__name__}: {exc}",
    }

  try:
    credential = DefaultAzureCredential()
    client = SubscriptionClient(credential)
  except Exception as exc:
    return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

  subscriptions: list[dict[str, Any]] = []
  try:
    for sub in client.subscriptions.list():
      subscriptions.append(
        {
          "subscription_id": getattr(sub, "subscription_id", None),
          "display_name": getattr(sub, "display_name", None),
          "state": getattr(sub, "state", None),
          "tenant_id": getattr(sub, "tenant_id", None),
        }
      )
      if len(subscriptions) >= max(0, int(max_subscriptions)):
        break
  except Exception as exc:
    return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

  return {"status": "ok", "subscriptions": {"count": len(subscriptions), "items": subscriptions}}


def main() -> None:
  import json

  print(json.dumps(get_snapshot(), indent=2, sort_keys=True))


if __name__ == "__main__":
  main()
