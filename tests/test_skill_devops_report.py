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


def test_devops_report_skips_all_when_env_missing(monkeypatch):
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

  module = _import_skill_script("devops_report")
  report = module.generate_report()

  assert report["snapshots"]["github"]["skipped"] is True
  assert report["snapshots"]["jenkins"]["skipped"] is True
  assert report["snapshots"]["azure"]["skipped"] is True
  assert report["snapshots"]["artifactory"]["skipped"] is True
