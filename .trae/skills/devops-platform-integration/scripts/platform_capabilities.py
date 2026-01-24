"""Detect platform integration availability using env/.env variables only."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import Any

from dotenv import load_dotenv


@dataclass(frozen=True)
class PlatformCapability:
  """Capability status for a single platform integration."""

  enabled: bool
  missing_env: list[str]
  reason: str
  next_steps: str


def _is_set(name: str) -> bool:
  value = os.environ.get(name)
  return bool(value)


def _load_dotenv_if_enabled() -> None:
  if os.environ.get("DEVOPS_MCPS_SKILL_IGNORE_DOTENV", "").strip().lower() in {
    "1",
    "true",
    "yes",
  }:
    return
  load_dotenv()


def _github_capability() -> PlatformCapability:
  if not _is_set("GITHUB_PERSONAL_ACCESS_TOKEN"):
    return PlatformCapability(
      enabled=False,
      missing_env=["GITHUB_PERSONAL_ACCESS_TOKEN"],
      reason="GitHub token is not configured.",
      next_steps="Set GITHUB_PERSONAL_ACCESS_TOKEN in env or .env.",
    )
  return PlatformCapability(
    enabled=True,
    missing_env=[],
    reason="GitHub token detected.",
    next_steps="",
  )


def _jenkins_capability() -> PlatformCapability:
  required = ["JENKINS_URL", "JENKINS_USER", "JENKINS_TOKEN"]
  missing = [name for name in required if not _is_set(name)]
  if missing:
    return PlatformCapability(
      enabled=False,
      missing_env=missing,
      reason="Jenkins credentials are not fully configured.",
      next_steps="Set JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN in env or .env.",
    )
  return PlatformCapability(
    enabled=True,
    missing_env=[],
    reason="Jenkins credentials detected.",
    next_steps="",
  )


def _azure_capability() -> PlatformCapability:
  required = ["AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET", "AZURE_TENANT_ID"]
  missing = [name for name in required if not _is_set(name)]
  if missing:
    return PlatformCapability(
      enabled=False,
      missing_env=missing,
      reason=(
        "Azure service principal credentials are not configured via env/.env. "
        "Azure CLI or managed identity authentication is not detected by this check."
      ),
      next_steps=(
        "Set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID in env or .env."
      ),
    )
  return PlatformCapability(
    enabled=True,
    missing_env=[],
    reason="Azure service principal credentials detected.",
    next_steps="",
  )


def _artifactory_capability() -> PlatformCapability:
  missing: list[str] = []
  if not _is_set("ARTIFACTORY_URL"):
    missing.append("ARTIFACTORY_URL")

  has_token = _is_set("ARTIFACTORY_IDENTITY_TOKEN")
  has_userpass = _is_set("ARTIFACTORY_USERNAME") and _is_set("ARTIFACTORY_PASSWORD")
  if not (has_token or has_userpass):
    missing.extend(
      [
        "ARTIFACTORY_IDENTITY_TOKEN",
        "ARTIFACTORY_USERNAME",
        "ARTIFACTORY_PASSWORD",
      ]
    )

  if missing:
    return PlatformCapability(
      enabled=False,
      missing_env=sorted(set(missing)),
      reason="Artifactory URL and authentication are not fully configured.",
      next_steps=(
        "Set ARTIFACTORY_URL and either ARTIFACTORY_IDENTITY_TOKEN or "
        "ARTIFACTORY_USERNAME + ARTIFACTORY_PASSWORD in env or .env."
      ),
    )

  return PlatformCapability(
    enabled=True,
    missing_env=[],
    reason="Artifactory configuration detected.",
    next_steps="",
  )


def get_platform_capabilities() -> dict[str, Any]:
  """Return platform capabilities based on env/.env presence only."""
  _load_dotenv_if_enabled()
  return {
    "github": asdict(_github_capability()),
    "jenkins": asdict(_jenkins_capability()),
    "azure": asdict(_azure_capability()),
    "artifactory": asdict(_artifactory_capability()),
  }


def main() -> None:
  print(json.dumps(get_platform_capabilities(), indent=2, sort_keys=True))


if __name__ == "__main__":
  main()
