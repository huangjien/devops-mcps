"""Generate a combined DevOps platform snapshot report (env/.env gated)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv


def _import_from_scripts(module_name: str):
  scripts_dir = Path(__file__).resolve().parent
  sys.path.insert(0, str(scripts_dir))
  try:
    return __import__(module_name)
  finally:
    try:
      sys.path.remove(str(scripts_dir))
    except ValueError:
      return


def _load_dotenv_if_enabled() -> None:
  if os.environ.get("DEVOPS_MCPS_SKILL_IGNORE_DOTENV", "").strip().lower() in {
    "1",
    "true",
    "yes",
  }:
    return
  load_dotenv()


def _run_snapshot(get_snapshot: Callable[[], dict[str, Any]]) -> dict[str, Any]:
  try:
    return get_snapshot()
  except Exception as exc:
    return {
      "status": "error",
      "error": f"{type(exc).__name__}: {exc}",
    }


def generate_report() -> dict[str, Any]:
  """Generate a combined report, skipping platforms without required env vars."""
  _load_dotenv_if_enabled()

  platform_capabilities = _import_from_scripts("platform_capabilities")
  capabilities: dict[str, Any] = platform_capabilities.get_platform_capabilities()

  report: dict[str, Any] = {"capabilities": capabilities, "snapshots": {}}

  github_enabled = bool(capabilities.get("github", {}).get("enabled"))
  if github_enabled:
    github_snapshot = _import_from_scripts("github_snapshot")
    report["snapshots"]["github"] = _run_snapshot(github_snapshot.get_snapshot)
  else:
    report["snapshots"]["github"] = {
      "skipped": True,
      "reason": capabilities.get("github", {}).get("reason", ""),
    }

  jenkins_enabled = bool(capabilities.get("jenkins", {}).get("enabled"))
  if jenkins_enabled:
    jenkins_snapshot = _import_from_scripts("jenkins_snapshot")
    report["snapshots"]["jenkins"] = _run_snapshot(jenkins_snapshot.get_snapshot)
  else:
    report["snapshots"]["jenkins"] = {
      "skipped": True,
      "reason": capabilities.get("jenkins", {}).get("reason", ""),
    }

  azure_enabled = bool(capabilities.get("azure", {}).get("enabled"))
  if azure_enabled:
    azure_snapshot = _import_from_scripts("azure_snapshot")
    report["snapshots"]["azure"] = _run_snapshot(azure_snapshot.get_snapshot)
  else:
    report["snapshots"]["azure"] = {
      "skipped": True,
      "reason": capabilities.get("azure", {}).get("reason", ""),
    }

  artifactory_enabled = bool(capabilities.get("artifactory", {}).get("enabled"))
  if artifactory_enabled:
    artifactory_snapshot = _import_from_scripts("artifactory_snapshot")
    report["snapshots"]["artifactory"] = _run_snapshot(
      artifactory_snapshot.get_snapshot
    )
  else:
    report["snapshots"]["artifactory"] = {
      "skipped": True,
      "reason": capabilities.get("artifactory", {}).get("reason", ""),
    }

  return report


def main() -> None:
  print(json.dumps(generate_report(), indent=2, sort_keys=True))


if __name__ == "__main__":
  main()
