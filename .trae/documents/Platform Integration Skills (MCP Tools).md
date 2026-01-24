## What I’ll Build
Create a new **skill folder** in this repo containing **pure Python scripts** (no FastMCP, no existing MCP tool functions) that:
1) check whether required secrets exist in **env or .env**, 2) skip missing integrations with a clear reason, and 3) can be composed to produce a unified DevOps “snapshot” report.

## Folder Layout
- `skills/devops-platform-integration/SKILL.md`
- `skills/devops-platform-integration/scripts/`
  - `platform_capabilities.py`
  - `devops_report.py`
  - `github_snapshot.py`
  - `jenkins_snapshot.py`
  - `azure_snapshot.py`
  - `artifactory_snapshot.py`
- `skills/devops-platform-integration/references/`
  - `env-vars.md` (required variables + examples)

## Script Responsibilities
- **platform_capabilities.py**
  - Calls `load_dotenv()`.
  - Checks env vars only (no network calls).
  - Outputs JSON with per-platform: `enabled`, `missing_env`, `reason`, `next_steps`.
- **devops_report.py**
  - Calls `platform_capabilities` first.
  - For each enabled platform, imports and runs the corresponding snapshot script.
  - For each disabled platform, adds `skipped: true` and `reason` to the report.
  - Outputs one combined JSON document.
- **github_snapshot.py**
  - Requires `GITHUB_PERSONAL_ACCESS_TOKEN`.
  - Uses PyGithub directly (not MCP tools) to fetch minimal safe info (e.g., current user login, rate limit summary).
- **jenkins_snapshot.py**
  - Requires `JENKINS_URL`, `JENKINS_USER`, `JENKINS_TOKEN`.
  - Uses `jenkinsapi` directly to fetch minimal safe info (e.g., master data + a short list of recent failed builds if feasible).
- **azure_snapshot.py**
  - Requires env-based service principal: `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`.
  - Uses Azure SDKs directly to list subscriptions (minimal).
  - If not present, skip with reason: env/.env-only check can’t detect Azure CLI/managed identity.
- **artifactory_snapshot.py**
  - Requires `ARTIFACTORY_URL` plus either `ARTIFACTORY_IDENTITY_TOKEN` or (`ARTIFACTORY_USERNAME` + `ARTIFACTORY_PASSWORD`).
  - Uses `requests` to call a lightweight endpoint (e.g., whoami/ping) for minimal connectivity/auth confirmation.

## Composition (“skills can work together”)
- Typical flow:
  1) Run `platform_capabilities.py` to see what’s configured.
  2) Run `devops_report.py` to gather info only for configured platforms.
  3) Optionally run any single snapshot script directly.

## Tests (so this is reliable)
- Add `tests/test_skill_platform_capabilities.py`:
  - Validates env-var detection logic with `monkeypatch`.
  - Ensures no secrets are printed.
- Add `tests/test_skill_devops_report.py`:
  - Verifies the report skips missing platforms cleanly.

## Non-Goals (per your request)
- No changes to FastMCP registration, `mcp_tools.py`, or any MCP tool usage.

If you confirm, I’ll implement the new `skills/devops-platform-integration/` folder, scripts, and tests.