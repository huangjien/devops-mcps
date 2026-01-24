# Environment Variables

The scripts in this skill load a `.env` file automatically (if present) and then inspect environment variables.

## GitHub

- Required:
  - `GITHUB_PERSONAL_ACCESS_TOKEN`
- Optional:
  - `GITHUB_API_URL` (for GitHub Enterprise API base URL)

## Jenkins

- Required:
  - `JENKINS_URL`
  - `JENKINS_USER`
  - `JENKINS_TOKEN`

### Optional: Include Build Logs

- `JENKINS_INCLUDE_LOGS` (true/false)
- `JENKINS_LOG_JOB` (job full name like `folder1/folder2/job-name`)
- `JENKINS_LOG_BUILD` (default: `lastBuild`, or a build number)
- `JENKINS_LOG_BYTES` (default: 8192, tail bytes pulled from consoleText)
- `JENKINS_LOG_TAIL_LINES` (default: 200, tail lines returned after truncation)
- `JENKINS_LOG_TIMEOUT_SECONDS` (default: 10)

## Azure (env/.env only)

The scripts treat Azure as enabled only when service principal variables are present:

- Required:
  - `AZURE_CLIENT_ID`
  - `AZURE_CLIENT_SECRET`
  - `AZURE_TENANT_ID`

## Artifactory

- Required:
  - `ARTIFACTORY_URL`
- Authentication (choose one):
  - `ARTIFACTORY_IDENTITY_TOKEN`
  - OR `ARTIFACTORY_USERNAME` and `ARTIFACTORY_PASSWORD`
