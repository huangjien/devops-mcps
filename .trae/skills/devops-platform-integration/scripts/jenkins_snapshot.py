"""Fetch a minimal Jenkins snapshot using env/.env credentials."""

from __future__ import annotations

import argparse
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


def _parse_bool(value: str) -> bool:
  return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _jenkins_job_path(job_full_name: str) -> str:
  normalized = job_full_name.strip().strip("/")
  if not normalized:
    return ""
  parts = [p for p in normalized.split("/") if p]
  return "/".join(["job/" + part for part in parts])


def _tail_lines(text: str, lines: int) -> str:
  if lines <= 0:
    return ""
  all_lines = text.splitlines()
  return "\n".join(all_lines[-lines:])


def _summarize_log(log_text: str) -> dict[str, Any]:
  keywords = ["ERROR", "Exception", "FAILED", "Traceback"]
  counts = {k: 0 for k in keywords}
  matched_lines: list[str] = []

  for line in log_text.splitlines():
    for keyword in keywords:
      if keyword in line:
        counts[keyword] += 1
        if len(matched_lines) < 25:
          matched_lines.append(line[:500])

  return {
    "line_count": len(log_text.splitlines()),
    "keyword_counts": counts,
    "matched_lines_sample": matched_lines,
  }


def _fetch_console_text(
  *,
  base_url: str,
  user: str,
  token: str,
  job_full_name: str,
  build: str,
  bytes_limit: int,
  timeout_seconds: float,
) -> dict[str, Any]:
  job_path = _jenkins_job_path(job_full_name)
  if not job_path:
    return {"status": "error", "error": "job_full_name is empty"}

  if not build:
    build = "lastBuild"

  try:
    import requests
  except Exception as exc:
    return {
      "status": "error",
      "error": f"requests import failed: {type(exc).__name__}: {exc}",
    }

  url = f"{base_url.rstrip('/')}/{job_path}/{build}/consoleText"

  try:
    response = requests.get(
      url,
      auth=(user, token),
      timeout=float(timeout_seconds),
      headers={"Accept": "text/plain"},
    )
  except Exception as exc:
    return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

  body = response.text or ""
  truncated = False
  if bytes_limit > 0:
    encoded = body.encode("utf-8", errors="replace")
    if len(encoded) > bytes_limit:
      truncated = True
      body = encoded[-bytes_limit:].decode("utf-8", errors="replace")

  return {
    "status": "ok" if response.status_code == 200 else "degraded",
    "status_code": response.status_code,
    "job_full_name": job_full_name,
    "build": build,
    "truncated": truncated,
    "log_tail": body,
    "log_summary": _summarize_log(body),
  }


def get_snapshot(max_jobs: int = 25) -> dict[str, Any]:
  """Return minimal Jenkins server information and a small job listing."""
  _load_dotenv_if_enabled()

  url = _get_env("JENKINS_URL")
  user = _get_env("JENKINS_USER")
  token = _get_env("JENKINS_TOKEN")

  missing = [n for n, v in [("JENKINS_URL", url), ("JENKINS_USER", user), ("JENKINS_TOKEN", token)] if not v]
  if missing:
    return {
      "skipped": True,
      "reason": "Jenkins credentials are not fully configured.",
      "missing_env": missing,
    }

  try:
    from jenkinsapi.jenkins import Jenkins
  except Exception as exc:
    return {
      "status": "error",
      "error": f"jenkinsapi import failed: {type(exc).__name__}: {exc}",
    }

  try:
    server = Jenkins(url, username=user, password=token)
  except Exception as exc:
    return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

  result: dict[str, Any] = {"status": "ok", "url": url}

  try:
    result["version"] = getattr(server, "version", None)
  except Exception:
    result["version"] = None

  try:
    jobs = list(server.get_jobs_list())
    result["jobs"] = {
      "count": len(jobs),
      "sample": jobs[: max(0, int(max_jobs))],
    }
  except Exception as exc:
    result["jobs"] = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

  include_logs = _parse_bool(_get_env("JENKINS_INCLUDE_LOGS") or "false")
  log_job = _get_env("JENKINS_LOG_JOB")
  if include_logs and log_job:
    build = _get_env("JENKINS_LOG_BUILD") or "lastBuild"
    try:
      bytes_limit = int(_get_env("JENKINS_LOG_BYTES") or "8192")
    except ValueError:
      bytes_limit = 8192
    try:
      timeout_seconds = float(_get_env("JENKINS_LOG_TIMEOUT_SECONDS") or "10")
    except ValueError:
      timeout_seconds = 10.0
    try:
      tail_lines = int(_get_env("JENKINS_LOG_TAIL_LINES") or "200")
    except ValueError:
      tail_lines = 200

    log_result = _fetch_console_text(
      base_url=url,
      user=user,
      token=token,
      job_full_name=log_job,
      build=build,
      bytes_limit=max(0, bytes_limit),
      timeout_seconds=max(1.0, timeout_seconds),
    )
    if isinstance(log_result.get("log_tail"), str) and tail_lines > 0:
      log_result["log_tail"] = _tail_lines(str(log_result["log_tail"]), tail_lines)
      log_result["log_summary"] = _summarize_log(str(log_result["log_tail"]))
    result["build_log"] = log_result
  elif include_logs and not log_job:
    result["build_log"] = {
      "skipped": True,
      "reason": "JENKINS_INCLUDE_LOGS is true but JENKINS_LOG_JOB is not set.",
      "missing_env": ["JENKINS_LOG_JOB"],
    }

  return result


def main() -> None:
  import json

  parser = argparse.ArgumentParser(description="Jenkins snapshot (optionally include build logs)")
  parser.add_argument("--max-jobs", type=int, default=25)
  parser.add_argument("--include-logs", action="store_true")
  parser.add_argument("--job", default="")
  parser.add_argument("--build", default="lastBuild")
  parser.add_argument("--log-bytes", type=int, default=8192)
  parser.add_argument("--tail-lines", type=int, default=200)
  parser.add_argument("--timeout-seconds", type=float, default=10.0)
  args = parser.parse_args()

  if args.include_logs:
    os.environ["JENKINS_INCLUDE_LOGS"] = "true"
    if args.job:
      os.environ["JENKINS_LOG_JOB"] = str(args.job)
    os.environ["JENKINS_LOG_BUILD"] = str(args.build)
    os.environ["JENKINS_LOG_BYTES"] = str(args.log_bytes)
    os.environ["JENKINS_LOG_TAIL_LINES"] = str(args.tail_lines)
    os.environ["JENKINS_LOG_TIMEOUT_SECONDS"] = str(args.timeout_seconds)

  print(json.dumps(get_snapshot(max_jobs=args.max_jobs), indent=2, sort_keys=True))


if __name__ == "__main__":
  main()
