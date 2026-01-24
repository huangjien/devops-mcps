import json
import sys
from importlib import import_module
from pathlib import Path


def _import_skill_script(module_name: str):
  scripts_dir = (
    Path(__file__).resolve().parents[1]
    / ".trae"
    / "skills"
    / "devops-platform-integration"
    / "scripts"
  )
  sys.path.insert(0, str(scripts_dir))
  try:
    return import_module(module_name)
  finally:
    try:
      sys.path.remove(str(scripts_dir))
    except ValueError:
      return


def test_platform_capabilities_all_missing(monkeypatch):
  monkeypatch.setenv("DEVOPS_MCPS_SKILL_IGNORE_DOTENV", "true")
  for name in [
    "GITHUB_PERSONAL_ACCESS_TOKEN",
    "JENKINS_URL",
    "JENKINS_USER",
    "JENKINS_TOKEN",
    "AZURE_CLIENT_ID",
    "AZURE_CLIENT_SECRET",
    "AZURE_TENANT_ID",
    "ARTIFACTORY_URL",
    "ARTIFACTORY_IDENTITY_TOKEN",
    "ARTIFACTORY_USERNAME",
    "ARTIFACTORY_PASSWORD",
    "JENKINS_INCLUDE_LOGS",
    "JENKINS_LOG_JOB",
    "JENKINS_LOG_BUILD",
    "JENKINS_LOG_BYTES",
    "JENKINS_LOG_TAIL_LINES",
    "JENKINS_LOG_TIMEOUT_SECONDS",
  ]:
    monkeypatch.delenv(name, raising=False)

  module = _import_skill_script("platform_capabilities")
  caps = module.get_platform_capabilities()

  assert caps["github"]["enabled"] is False
  assert caps["jenkins"]["enabled"] is False
  assert caps["azure"]["enabled"] is False
  assert caps["artifactory"]["enabled"] is False


def test_platform_capabilities_no_secret_echo(monkeypatch):
  monkeypatch.setenv("DEVOPS_MCPS_SKILL_IGNORE_DOTENV", "true")
  secret = "super-secret-value"
  monkeypatch.setenv("GITHUB_PERSONAL_ACCESS_TOKEN", secret)
  monkeypatch.setenv("ARTIFACTORY_URL", "https://example.invalid/artifactory")
  monkeypatch.setenv("ARTIFACTORY_IDENTITY_TOKEN", secret)

  module = _import_skill_script("platform_capabilities")
  caps = module.get_platform_capabilities()

  assert caps["github"]["enabled"] is True
  assert caps["artifactory"]["enabled"] is True
  assert secret not in json.dumps(caps)
