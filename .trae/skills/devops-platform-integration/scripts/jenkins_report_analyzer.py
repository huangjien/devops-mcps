"""Analyze a Jenkins report job console log and highlight anomalies.

Rules implemented:
- Highlight deployments with booked time >= N days ago.
- If a VM name ends with "-builder", it must be in the expected resource group.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

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


def _tail_lines(text: str, lines: int) -> str:
  if lines <= 0:
    return ""
  all_lines = text.splitlines()
  return "\n".join(all_lines[-lines:])


def _parse_datetime(text: str) -> datetime | None:
  value = text.strip()
  if not value:
    return None

  value = value.replace("UTC", "").strip()
  if value.endswith("Z") and "T" in value:
    value = value[:-1] + "+00:00"

  for fmt in [
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S%z",
    "%m/%d/%Y",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y %H:%M:%S",
  ]:
    try:
      dt = datetime.strptime(value, fmt)
      if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
      return dt.astimezone(timezone.utc)
    except ValueError:
      continue

  try:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
      dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
  except Exception:
    return None


def _find_markdown_tables(lines: list[str]) -> list[list[list[str]]]:
  tables: list[list[list[str]]] = []
  current: list[list[str]] = []

  def _flush():
    nonlocal current
    if current:
      tables.append(current)
      current = []

  for line in lines:
    stripped = line.strip()
    if "|" in stripped and stripped.count("|") >= 2:
      row = [cell.strip() for cell in stripped.strip("|").split("|")]
      current.append(row)
    else:
      _flush()
  _flush()
  return tables


def _keyword_findings(log_text: str) -> dict[str, Any]:
  keywords = ["ERROR", "Exception", "FAILED", "Traceback", "FATAL"]
  counts = {k: 0 for k in keywords}
  matched_lines: list[str] = []
  extra_highlights: list[str] = []

  for line in log_text.splitlines():
    for keyword in keywords:
      if keyword in line:
        counts[keyword] += 1
        if len(matched_lines) < 50:
          matched_lines.append(line[:500])

    if (
      "Warning: A secret was passed to" in line
      and "Groovy String interpolation" in log_text
    ):
      if len(extra_highlights) < 10:
        extra_highlights.append(line[:500])

  status = "ok"
  if sum(counts.values()) > 0:
    status = "attention"
  if extra_highlights:
    status = "attention"

  return {
    "status": status,
    "keyword_counts": counts,
    "matched_lines_sample": matched_lines,
    "extra_highlights": extra_highlights,
  }


@dataclass(frozen=True)
class DeploymentBookingIssue:
  deployment: str
  booked_time_utc: str | None
  age_days: float | None
  raw: str


@dataclass(frozen=True)
class BuilderRgIssue:
  vm_name: str
  resource_group: str | None
  expected_resource_group: str
  raw: str


def _extract_deployment_bookings(
  log_text: str, *, now_utc: datetime, threshold_days: float
) -> list[DeploymentBookingIssue]:
  issues: list[DeploymentBookingIssue] = []
  lines = log_text.splitlines()

  node_created_pattern = re.compile(
    r"^\s*node:\s*(?P<deployment>\S+)\s+created:\s*(?P<booked>\S+)\s*$"
  )
  for line in lines:
    match = node_created_pattern.match(line)
    if not match:
      continue
    deployment = match.group("deployment").strip()
    booked_raw = match.group("booked").strip()
    dt = _parse_datetime(booked_raw)
    if not dt:
      continue
    age_days = (now_utc - dt).total_seconds() / 86400.0
    if age_days >= threshold_days:
      issues.append(
        DeploymentBookingIssue(
          deployment=deployment,
          booked_time_utc=dt.isoformat(),
          age_days=round(age_days, 2),
          raw=line[:500],
        )
      )

  tables = _find_markdown_tables(lines)
  for table in tables:
    if len(table) < 2:
      continue
    header = [c.lower() for c in table[0]]
    if not any("deploy" in c for c in header):
      continue
    if not any("book" in c for c in header):
      continue

    try:
      deploy_idx = next(i for i, c in enumerate(header) if "deploy" in c)
      booked_idx = next(i for i, c in enumerate(header) if "book" in c)
    except StopIteration:
      continue

    for row in table[1:]:
      if len(row) <= max(deploy_idx, booked_idx):
        continue
      deployment = row[deploy_idx].strip()
      booked_raw = row[booked_idx].strip()
      if not deployment or not booked_raw:
        continue
      dt = _parse_datetime(booked_raw)
      if not dt:
        continue
      age_days = (now_utc - dt).total_seconds() / 86400.0
      if age_days >= threshold_days:
        issues.append(
          DeploymentBookingIssue(
            deployment=deployment,
            booked_time_utc=dt.isoformat(),
            age_days=round(age_days, 2),
            raw=" | ".join(row),
          )
        )

  pattern = re.compile(
    r"(?i)deployment\s*[:=]\s*(?P<deployment>[A-Za-z0-9._-]+).*?"
    r"book(?:ed)?(?:\s*time)?\s*[:=]\s*(?P<booked>[^\n]+)"
  )
  for line in lines:
    match = pattern.search(line)
    if not match:
      continue
    deployment = match.group("deployment").strip()
    booked_raw = match.group("booked").strip()
    dt = _parse_datetime(booked_raw)
    if not dt:
      continue
    age_days = (now_utc - dt).total_seconds() / 86400.0
    if age_days >= threshold_days:
      issues.append(
        DeploymentBookingIssue(
          deployment=deployment,
          booked_time_utc=dt.isoformat(),
          age_days=round(age_days, 2),
          raw=line[:500],
        )
      )

  unique: dict[tuple[str, str | None], DeploymentBookingIssue] = {}
  for issue in issues:
    unique[(issue.deployment, issue.booked_time_utc)] = issue
  return list(unique.values())


def _extract_builder_rg_issues(
  log_text: str, *, expected_resource_group: str
) -> list[BuilderRgIssue]:
  issues: list[BuilderRgIssue] = []
  lines = log_text.splitlines()
  tables = _find_markdown_tables(lines)

  for table in tables:
    if len(table) < 2:
      continue
    header = [c.lower() for c in table[0]]
    if not any("vm" in c for c in header):
      continue
    if not any("rg" == c or "resource group" in c or c.endswith("rg") for c in header):
      continue

    try:
      vm_idx = next(i for i, c in enumerate(header) if "vm" in c)
    except StopIteration:
      continue

    rg_idx = None
    for i, c in enumerate(header):
      if c == "rg" or "resource group" in c or c.endswith(" rg") or c.endswith("_rg"):
        rg_idx = i
        break
    if rg_idx is None:
      continue

    for row in table[1:]:
      if len(row) <= max(vm_idx, rg_idx):
        continue
      vm_name = row[vm_idx].strip()
      rg = row[rg_idx].strip() or None
      if not vm_name:
        continue
      if vm_name.endswith("-builder") and rg != expected_resource_group:
        issues.append(
          BuilderRgIssue(
            vm_name=vm_name,
            resource_group=rg,
            expected_resource_group=expected_resource_group,
            raw=" | ".join(row),
          )
        )

  pattern = re.compile(
    r"(?i)\bvm\b\s*[:=]\s*(?P<vm>[A-Za-z0-9._-]+)\s+.*?\brg\b\s*[:=]\s*(?P<rg>[A-Za-z0-9._-]+)"
  )
  for line in lines:
    match = pattern.search(line)
    if not match:
      continue
    vm = match.group("vm").strip()
    rg = match.group("rg").strip()
    if vm.endswith("-builder") and rg != expected_resource_group:
      issues.append(
        BuilderRgIssue(
          vm_name=vm,
          resource_group=rg,
          expected_resource_group=expected_resource_group,
          raw=line[:500],
        )
      )

  resource_group_pattern = re.compile(
    r"(?i)\bvm\b\s*:\s*(?P<vm>[A-Za-z0-9._-]+)\s*,\s*resource\s+group\s*:\s*(?P<rg>[A-Za-z0-9._-]+)"
  )
  for line in lines:
    match = resource_group_pattern.search(line)
    if not match:
      continue
    vm = match.group("vm").strip()
    rg = match.group("rg").strip()
    if vm.endswith("-builder") and rg != expected_resource_group:
      issues.append(
        BuilderRgIssue(
          vm_name=vm,
          resource_group=rg,
          expected_resource_group=expected_resource_group,
          raw=line[:500],
        )
      )

  unique: dict[tuple[str, str | None], BuilderRgIssue] = {}
  for issue in issues:
    unique[(issue.vm_name, issue.resource_group)] = issue
  return list(unique.values())


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
    return {"status": "error", "error": "job name is empty"}

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
    "url": url,
    "truncated": truncated,
    "log_tail": body,
  }


def _extract_platform_mismatches(log_text: str) -> list[dict[str, Any]]:
  pattern = re.compile(
    r"^\s*(?P<count>\d+)\s+In\s+(?P<a>Azure|Fluxy|Jenkins)\s+not\s+in\s+(?P<b>Azure|Fluxy|Jenkins)\s*:\s*$"
  )
  mismatches: list[dict[str, Any]] = []
  for line in log_text.splitlines():
    match = pattern.match(line)
    if not match:
      continue
    mismatches.append(
      {
        "count": int(match.group("count")),
        "from": match.group("a"),
        "to_missing_in": match.group("b"),
        "raw": line.strip()[:200],
      }
    )
  return mismatches


def analyze_jenkins_report(
  *,
  job: str,
  build: str = "lastBuild",
  threshold_days: float = 3.0,
  expected_builder_rg: str = "RG-SPMDEV",
  log_bytes: int = 400_000,
  tail_lines: int = 4000,
  timeout_seconds: float = 15.0,
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

  log_result = _fetch_console_text(
    base_url=base_url,
    user=user,
    token=token,
    job_full_name=job,
    build=build,
    bytes_limit=max(0, int(log_bytes)),
    tail_lines_count=max(0, int(tail_lines)),
    timeout_seconds=max(1.0, float(timeout_seconds)),
  )
  if log_result.get("status") not in {"ok", "degraded"}:
    return {"status": "error", "error": log_result}

  log_tail = str(log_result.get("log_tail") or "")
  now_utc = datetime.now(timezone.utc)

  keyword = _keyword_findings(log_tail)
  mismatches = _extract_platform_mismatches(log_tail)
  deployment_issues = _extract_deployment_bookings(
    log_tail, now_utc=now_utc, threshold_days=float(threshold_days)
  )
  builder_issues = _extract_builder_rg_issues(
    log_tail, expected_resource_group=str(expected_builder_rg)
  )

  status = "ok"
  highlights: list[str] = []
  keyword_counts = keyword.get("keyword_counts", {})
  if isinstance(keyword_counts, dict) and sum(int(v) for v in keyword_counts.values()) > 0:
    status = "attention"
    highlights.append("Log contains error keywords (ERROR/FAILED/Traceback/etc).")
  extra = keyword.get("extra_highlights", [])
  if isinstance(extra, list) and extra:
    status = "attention"
    highlights.append("Log contains Jenkins secret interpolation warning(s).")
  if deployment_issues:
    status = "attention"
    highlights.append(
      f"Found {len(deployment_issues)} deployment(s) booked >= {threshold_days} day(s) ago."
    )
  if builder_issues:
    status = "attention"
    highlights.append(
      f"Found {len(builder_issues)} builder VM(s) not in {expected_builder_rg}."
    )
  mismatch_count = sum(m.get("count", 0) for m in mismatches if isinstance(m.get("count"), int))
  if mismatch_count > 0:
    status = "attention"
    highlights.append("Platform inventory mismatches detected (Azure/Fluxy/Jenkins).")

  return {
    "status": status,
    "job": job,
    "build": build,
    "highlights": highlights,
    "log": {k: v for k, v in log_result.items() if k != "log_tail"},
    "keyword_findings": keyword,
    "platform_mismatches": mismatches,
    "deployment_booked_3plus_days": [asdict(x) for x in deployment_issues],
    "builder_rg_violations": [asdict(x) for x in builder_issues],
  }


def main() -> None:
  parser = argparse.ArgumentParser(description="Analyze a Jenkins report job console log")
  parser.add_argument("--job", required=True)
  parser.add_argument("--build", default="lastBuild")
  parser.add_argument("--threshold-days", type=float, default=3.0)
  parser.add_argument("--expected-builder-rg", default="RG-SPMDEV")
  parser.add_argument("--log-bytes", type=int, default=400_000)
  parser.add_argument("--tail-lines", type=int, default=4000)
  parser.add_argument("--timeout-seconds", type=float, default=15.0)
  args = parser.parse_args()

  result = analyze_jenkins_report(
    job=str(args.job),
    build=str(args.build),
    threshold_days=float(args.threshold_days),
    expected_builder_rg=str(args.expected_builder_rg),
    log_bytes=int(args.log_bytes),
    tail_lines=int(args.tail_lines),
    timeout_seconds=float(args.timeout_seconds),
  )
  print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
  main()
