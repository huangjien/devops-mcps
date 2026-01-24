"""Fetch a minimal GitHub snapshot using env/.env credentials."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv


def _get_token() -> str:
  return os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN", "").strip()


def _get_api_url() -> str:
  return os.environ.get("GITHUB_API_URL", "").strip()


def _load_dotenv_if_enabled() -> None:
  if os.environ.get("DEVOPS_MCPS_SKILL_IGNORE_DOTENV", "").strip().lower() in {
    "1",
    "true",
    "yes",
  }:
    return
  load_dotenv()


def get_snapshot() -> dict[str, Any]:
  """Return minimal GitHub account and rate-limit information."""
  _load_dotenv_if_enabled()
  token = _get_token()
  if not token:
    return {
      "skipped": True,
      "reason": "GITHUB_PERSONAL_ACCESS_TOKEN is not configured.",
    }

  try:
    from github import Github
  except Exception as exc:
    return {
      "status": "error",
      "error": f"PyGithub import failed: {type(exc).__name__}: {exc}",
    }

  api_url = _get_api_url()
  client = Github(login_or_token=token, base_url=api_url) if api_url else Github(token)

  user = client.get_user()
  result: dict[str, Any] = {
    "status": "ok",
    "user": {
      "login": getattr(user, "login", None),
      "name": getattr(user, "name", None),
      "type": getattr(user, "type", None),
    },
  }

  try:
    rate = client.get_rate_limit()
    core = getattr(rate, "core", None)
    result["rate_limit"] = {
      "core_remaining": getattr(core, "remaining", None),
      "core_limit": getattr(core, "limit", None),
      "core_reset": getattr(core, "reset", None).isoformat()
      if getattr(core, "reset", None)
      else None,
    }
  except Exception as exc:
    result["rate_limit"] = {
      "status": "error",
      "error": f"{type(exc).__name__}: {exc}",
    }

  return result


def main() -> None:
  import json

  print(json.dumps(get_snapshot(), indent=2, sort_keys=True))


if __name__ == "__main__":
  main()
