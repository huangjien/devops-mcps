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


def test_jenkins_report_analyzer_skips_without_env(monkeypatch):
  monkeypatch.setenv("DEVOPS_MCPS_SKILL_IGNORE_DOTENV", "true")
  monkeypatch.delenv("JENKINS_URL", raising=False)
  monkeypatch.delenv("JENKINS_USER", raising=False)
  monkeypatch.delenv("JENKINS_TOKEN", raising=False)

  module = _import_skill_script("jenkins_report_analyzer")
  result = module.analyze_jenkins_report(job="DevOps-Infra-Status-Report")

  assert result["skipped"] is True
  assert "missing_env" in result
