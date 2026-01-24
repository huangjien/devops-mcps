"""List Jenkins failed builds within a recent time window (env/.env gated)."""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
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


def _jenkins_job_path(job_full_name: str) -> str:
  normalized = job_full_name.strip().strip("/")
  if not normalized:
    return ""
  parts = [p for p in normalized.split("/") if p]
  return "/".join(["job/" + part for part in parts])


def _iso_from_ms(timestamp_ms: int | None) -> str | None:
  if timestamp_ms is None:
    return None
  try:
    dt = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc)
    return dt.isoformat()
  except Exception:
    return None


def _parse_bool(value: str) -> bool:
  return value.strip().lower() in {"1", "true", "yes", "y", "on"}


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
  tail_lines_count: int,
  timeout_seconds: float,
) -> dict[str, Any]:
  job_path = _jenkins_job_path(job_full_name)
  if not job_path:
    return {"status": "error", "error": "job_full_name is empty"}

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

  body = _tail_lines(body, tail_lines_count)
  return {
    "status": "ok" if response.status_code == 200 else "degraded",
    "status_code": response.status_code,
    "job_full_name": job_full_name,
    "build": build,
    "truncated": truncated,
    "log_tail": body,
    "log_summary": _summarize_log(body),
  }


@dataclass(frozen=True)
class FailureRecord:
  job_full_name: str
  build_number: int | None
  build_url: str | None
  result: str | None
  timestamp_ms: int | None
  timestamp_utc: str | None
  age_seconds: int | None
  color: str | None


def _list_job_names(server, max_jobs: int) -> list[str]:
  jobs = list(server.get_jobs_list())
  if max_jobs <= 0:
    return jobs
  return jobs[:max_jobs]


def _fetch_job_last_failed_build(
  *,
  base_url: str,
  user: str,
  token: str,
  job_full_name: str,
  timeout_seconds: float,
) -> dict[str, Any]:
  job_path = _jenkins_job_path(job_full_name)
  if not job_path:
    return {"status": "error", "error": "job_full_name is empty"}

  try:
    import requests
  except Exception as exc:
    return {
      "status": "error",
      "error": f"requests import failed: {type(exc).__name__}: {exc}",
    }

  tree = (
    "fullName,name,url,color,lastFailedBuild[number,url,timestamp,result,building]"
  )
  url = f"{base_url.rstrip('/')}/{job_path}/api/json"
  try:
    response = requests.get(
      url,
      auth=(user, token),
      timeout=float(timeout_seconds),
      params={"tree": tree},
      headers={"Accept": "application/json"},
    )
  except Exception as exc:
    return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

  if response.status_code != 200:
    return {
      "status": "degraded",
      "status_code": response.status_code,
      "error": (response.text or "").strip()[:500],
    }

  try:
    return {"status": "ok", "data": response.json()}
  except Exception as exc:
    return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}


def get_recent_failures(
  *,
  hours: float = 8.0,
  max_jobs: int = 500,
  max_results: int = 50,
  include_logs: bool = False,
  log_bytes: int = 8192,
  log_tail_lines: int = 200,
  log_timeout_seconds: float = 10.0,
  api_timeout_seconds: float = 8.0,
) -> dict[str, Any]:
  _load_dotenv_if_enabled()

  base_url = _get_env("JENKINS_URL")
  user = _get_env("JENKINS_USER")
  token = _get_env("JENKINS_TOKEN")

  missing = [
    n
    for n, v in [("JENKINS_URL", base_url), ("JENKINS_USER", user), ("JENKINS_TOKEN", token)]
    if not v
  ]
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

  now_s = time.time()
  window_s = float(hours) * 3600.0
  threshold_ms = int((now_s - window_s) * 1000.0)

  try:
    server = Jenkins(base_url, username=user, password=token)
  except Exception as exc:
    return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

  job_names = _list_job_names(server, max_jobs=max_jobs)
  failures: list[FailureRecord] = []
  errors: list[dict[str, Any]] = []

  for job_full_name in job_names:
    fetched = _fetch_job_last_failed_build(
      base_url=base_url,
      user=user,
      token=token,
      job_full_name=job_full_name,
      timeout_seconds=max(1.0, float(api_timeout_seconds)),
    )
    if fetched.get("status") != "ok":
      errors.append({"job_full_name": job_full_name, "error": fetched})
      continue

    data = fetched.get("data", {})
    last_failed = data.get("lastFailedBuild")
    if not isinstance(last_failed, dict):
      continue

    timestamp_ms = last_failed.get("timestamp")
    if not isinstance(timestamp_ms, int):
      continue

    if timestamp_ms < threshold_ms:
      continue

    result = last_failed.get("result")
    build_number = last_failed.get("number")
    build_url = last_failed.get("url")
    color = data.get("color")

    age_seconds = int(max(0.0, now_s - (timestamp_ms / 1000.0)))
    failures.append(
      FailureRecord(
        job_full_name=str(data.get("fullName") or job_full_name),
        build_number=int(build_number) if isinstance(build_number, int) else None,
        build_url=str(build_url) if isinstance(build_url, str) else None,
        result=str(result) if isinstance(result, str) else None,
        timestamp_ms=timestamp_ms,
        timestamp_utc=_iso_from_ms(timestamp_ms),
        age_seconds=age_seconds,
        color=str(color) if isinstance(color, str) else None,
      )
    )

  failures.sort(key=lambda f: f.timestamp_ms or 0, reverse=True)
  if max_results > 0:
    failures = failures[:max_results]

  response: dict[str, Any] = {
    "status": "ok",
    "hours": float(hours),
    "jobs_scanned": len(job_names),
    "failures_found": len(failures),
    "failures": [asdict(f) for f in failures],
    "errors": errors[:50],
  }

  if include_logs and failures:
    logs: dict[str, Any] = {}
    for record in failures:
      if record.build_number is None:
        continue
      logs_key = f"{record.job_full_name}#{record.build_number}"
      logs[logs_key] = _fetch_console_text(
        base_url=base_url,
        user=user,
        token=token,
        job_full_name=record.job_full_name,
        build=str(record.build_number),
        bytes_limit=max(0, int(log_bytes)),
        tail_lines_count=max(0, int(log_tail_lines)),
        timeout_seconds=max(1.0, float(log_timeout_seconds)),
      )
    response["logs"] = logs

  return response


def main() -> None:
  parser = argparse.ArgumentParser(description="List Jenkins failures in a recent time window")
  parser.add_argument("--hours", type=float, default=8.0)
  parser.add_argument("--max-jobs", type=int, default=500)
  parser.add_argument("--max-results", type=int, default=50)
  parser.add_argument("--include-logs", action="store_true")
  parser.add_argument("--log-bytes", type=int, default=8192)
  parser.add_argument("--log-tail-lines", type=int, default=200)
  parser.add_argument("--log-timeout-seconds", type=float, default=10.0)
  parser.add_argument("--api-timeout-seconds", type=float, default=8.0)
  args = parser.parse_args()

  env_include_logs = _parse_bool(_get_env("JENKINS_INCLUDE_LOGS") or "false")
  include_logs = bool(args.include_logs or env_include_logs)

  report = get_recent_failures(
    hours=args.hours,
    max_jobs=args.max_jobs,
    max_results=args.max_results,
    include_logs=include_logs,
    log_bytes=args.log_bytes,
    log_tail_lines=args.log_tail_lines,
    log_timeout_seconds=args.log_timeout_seconds,
    api_timeout_seconds=args.api_timeout_seconds,
  )
  print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
  main()
