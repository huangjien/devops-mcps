"""Fetch a minimal Artifactory snapshot using env/.env credentials."""

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


def _build_auth() -> tuple[dict[str, str], tuple[str, str] | None]:
  identity_token = _get_env("ARTIFACTORY_IDENTITY_TOKEN")
  if identity_token:
    return {"Authorization": "Bearer " + identity_token}, None

  username = _get_env("ARTIFACTORY_USERNAME")
  password = _get_env("ARTIFACTORY_PASSWORD")
  if username and password:
    return {}, (username, password)

  return {}, None


def get_snapshot(timeout_seconds: float = 10.0) -> dict[str, Any]:
  """Return minimal Artifactory connectivity/auth information."""
  _load_dotenv_if_enabled()

  base_url = _get_env("ARTIFACTORY_URL").rstrip("/")
  if not base_url:
    return {
      "skipped": True,
      "reason": "ARTIFACTORY_URL is not configured.",
      "missing_env": ["ARTIFACTORY_URL"],
    }

  headers, basic_auth = _build_auth()
  if basic_auth is None and not headers:
    return {
      "skipped": True,
      "reason": "Artifactory authentication is not configured.",
      "missing_env": [
        "ARTIFACTORY_IDENTITY_TOKEN",
        "ARTIFACTORY_USERNAME",
        "ARTIFACTORY_PASSWORD",
      ],
    }

  try:
    import requests
  except Exception as exc:
    return {
      "status": "error",
      "error": f"requests import failed: {type(exc).__name__}: {exc}",
    }

  ping_url = f"{base_url}/api/system/ping"
  try:
    response = requests.get(
      ping_url,
      headers=headers if headers else None,
      auth=basic_auth,
      timeout=float(timeout_seconds),
    )
  except Exception as exc:
    return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

  body = (response.text or "").strip()
  body_preview = body[:200]
  return {
    "status": "ok" if response.status_code == 200 else "degraded",
    "url": base_url,
    "ping": {
      "status_code": response.status_code,
      "body_preview": body_preview,
    },
  }


def main() -> None:
  import json

  print(json.dumps(get_snapshot(), indent=2, sort_keys=True))


if __name__ == "__main__":
  main()
