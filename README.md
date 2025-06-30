# DevOps MCP Server

[![PyPI version](https://badge.fury.io/py/devops-mcps.svg)](https://badge.fury.io/py/devops-mcps)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen.svg)](https://github.com/huangjien/devops-mcps)

A [FastMCP](https://github.com/modelcontextprotocol/fastmcp)-based MCP server providing a suite of DevOps tools and integrations.

This server operates in a read-only manner, retrieving data for analysis and display without modifying your systems. It's designed with safety in mind for DevOps environments.

Certified by [MCP Review](https://mcpreview.com/mcp-servers/huangjien/devops-mcps)

## Features

The DevOps MCP Server integrates with various essential DevOps platforms:

### GitHub Integration

-   **Repository Management**: Search and view repository details.
-   **File Access**: Retrieve file contents from repositories.
-   **Issue Tracking**: Manage and track issues.
-   **Code Search**: Perform targeted code searches.
-   **Commit History**: View commit history for branches.
-   **Public & Enterprise Support**: Automatically detects and connects to both public GitHub and GitHub Enterprise instances (configurable via `GITHUB_API_URL`).

### Jenkins Integration

-   **Job Management**: List and manage Jenkins jobs.
-   **Build Logs**: Retrieve and analyze build logs.
-   **View Management**: Access and manage Jenkins views.
-   **Build Parameters**: Inspect parameters used for builds.
-   **Failure Monitoring**: Identify and monitor recent failed builds.

### Artifactory Integration

-   **Repository Browsing**: List items (files and directories) within Artifactory repositories.
-   **Artifact Search**: Search for artifacts by name or path across multiple repositories using Artifactory Query Language (AQL).
-   **Item Details**: Retrieve metadata and properties for specific files and directories.
-   **Authentication**: Supports both token-based and username/password authentication.

## Installation

Install the package using pip:

```bash
pip install devops-mcps
```

## Usage

Run the MCP server directly:

```bash
devops-mcps
```

### Transport Configuration

The server supports two communication transport types:

-   `stdio` (default): Standard input/output.
-   `stream_http`: HTTP streaming transport.

**Local Usage:**

```bash
# Default stdio transport
devops-mcps

# stream_http transport (runs HTTP server on 127.0.0.1:3721/mcp by default)
devops-mcps --transport stream_http
```

**UVX Usage:**

If using [UVX](https://github.com/modelcontextprotocol/uvx), first install the tools:

```bash
uvx install
```

Then run:

```bash
# Default stdio transport
uvx run devops-mcps

# stream_http transport
uvx run devops-mcps-stream-http
```

## Configuration

Configure the server using environment variables:

**Required:**

```bash
# GitHub
export GITHUB_PERSONAL_ACCESS_TOKEN="your_github_token"
# Optional: For GitHub Enterprise, set your API endpoint
# export GITHUB_API_URL="https://github.mycompany.com"

# Jenkins
export JENKINS_URL="your_jenkins_url"
export JENKINS_USER="your_jenkins_username"
export JENKINS_TOKEN="your_jenkins_api_token_or_password"

# Artifactory
export ARTIFACTORY_URL="https://your-artifactory-instance.example.com"
# Choose ONE authentication method:
export ARTIFACTORY_IDENTITY_TOKEN="your_artifactory_identity_token"
# OR
export ARTIFACTORY_USERNAME="your_artifactory_username"
export ARTIFACTORY_PASSWORD="your_artifactory_password"
```

**Optional:**

```bash
# Jenkins Log Length (default: 5120 bytes)
export LOG_LENGTH=10240

# MCP Server Port for stream_http transport (default: 3721)
export MCP_PORT=3721

# Dynamic Prompts (optional)
export PROMPTS_FILE="example_prompts.json"
```

**Note**: `LOG_LENGTH` controls the amount of Jenkins log data retrieved. Adjust as needed.

**Alternative: Using .env file**

You can also create a `.env` file in the project root directory instead of setting environment variables manually:

```bash
# .env file
GITHUB_PERSONAL_ACCESS_TOKEN=your_github_token_here
PROMPTS_FILE=example_prompts.json
# Add other optional environment variables as needed
```

The server will automatically load environment variables from the `.env` file when it starts.

### Dynamic Prompts

The server supports loading custom prompts from a JSON file. Set the `PROMPTS_FILE` environment variable to the path of your prompts configuration file.

**Prompts File Format:**

```json
{
  "prompts": [
    {
      "name": "github_repo_analysis",
      "description": "Analyze a GitHub repository for DevOps insights",
      "template": "Please analyze the GitHub repository {{owner}}/{{repo}} and provide insights on:\n\n1. Repository structure and organization\n2. CI/CD pipeline configuration\n3. Code quality indicators\n4. Security considerations\n5. Documentation quality\n\n{{#include_issues}}Also include analysis of recent issues and their resolution patterns.{{/include_issues}}",
      "arguments": [
        {
          "name": "owner",
          "description": "GitHub repository owner",
          "required": true
        },
        {
          "name": "repo",
          "description": "GitHub repository name",
          "required": true
        },
        {
          "name": "include_issues",
          "description": "Include analysis of repository issues",
          "required": false
        }
      ]
    }
  ]
}
```

### Using Prompts

The DevOps MCP Server provides dynamic prompts that help you perform common DevOps tasks. Here's how to use the available prompts:

#### Available Prompts

1. **`quick_repo_check`** - Quickly check a GitHub repository's basic information and recent activity
2. **`build_troubleshoot`** - Troubleshoot Jenkins build failures with detailed analysis

#### Using the `build_troubleshoot` Prompt

**Purpose:** Analyze Jenkins build failures with detailed analysis and actionable recommendations.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_name` | string | ✅ Yes | Jenkins job name |
| `build_number` | string | ❌ No | Build number to analyze (use -1 for latest) |
| `include_logs` | boolean | ❌ No | Whether to include build logs in analysis |

**Usage Examples:**

```
# Basic usage (latest build)
Prompt: build_troubleshoot
Parameters:
- job_name: "my-application-build"

# Specific build number
Prompt: build_troubleshoot
Parameters:
- job_name: "my-application-build"
- build_number: "42"

# With build logs
Prompt: build_troubleshoot
Parameters:
- job_name: "my-application-build"
- build_number: "42"
- include_logs: true
```

**What it does:**
1. Gets build status and basic information for the specified job
2. Retrieves and analyzes build logs (if `include_logs` is true)
3. Identifies potential failure causes based on the build data
4. Suggests troubleshooting steps with actionable recommendations

#### Using the `quick_repo_check` Prompt

**Purpose:** Quickly analyze a GitHub repository's basic information and recent activity.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_name` | string | ✅ Yes | Repository name in format 'owner/repo' |

**Usage Example:**

```
Prompt: quick_repo_check
Parameters:
- repo_name: "facebook/react"
```

**What it does:**
1. Gets basic repository information
2. Lists recent commits (last 10)
3. Checks open issues count
4. Reviews README content if available
5. Provides a summary of the repository's current state and activity level

#### Prerequisites

To use Jenkins-related prompts like `build_troubleshoot`, ensure you have:

```bash
# Required Jenkins environment variables
export JENKINS_URL="https://your-jenkins-server.com"
export JENKINS_USER="your-username"
export JENKINS_TOKEN="your-api-token"
```

To use GitHub-related prompts like `quick_repo_check`, ensure you have:

```bash
# Required GitHub environment variable
export GITHUB_PERSONAL_ACCESS_TOKEN="your_github_token"
```

**Template Variables:**
- Use `{{variable_name}}` for simple variable substitution
- Use `{{#variable_name}}...{{/variable_name}}` for conditional blocks (shown if variable has a value)
- Use `{{^variable_name}}...{{/variable_name}}` for negative conditional blocks (shown if variable is empty/null)

**Available Tools for Prompts:**
Your prompts can reference any of the available MCP tools:
- GitHub tools: `search_repositories`, `get_file_contents`, `list_commits`, `list_issues`, etc.
- Jenkins tools: `get_jenkins_jobs`, `get_jenkins_build_log`, `get_recent_failed_jenkins_builds`, etc.
- Azure tools: `get_azure_subscriptions`, `list_azure_vms`, `list_aks_clusters`, etc.
- Artifactory tools: `list_artifactory_items`, `search_artifactory_items`, `get_artifactory_item_info`, etc.

## Docker

Build the Docker image:

```bash
docker build -t devops-mcps .
```

Run the container:

```bash
# Stdio transport (interactive)
docker run -i --rm \
  -e GITHUB_PERSONAL_ACCESS_TOKEN="..." \
  -e JENKINS_URL="..." \
  -e JENKINS_USER="..." \
  -e JENKINS_TOKEN="..." \
  -e ARTIFACTORY_URL="..." \
  -e ARTIFACTORY_IDENTITY_TOKEN="..." \
  devops-mcps

# stream_http transport (background, HTTP server on 127.0.0.1:3721/mcp by default)
docker run -d -p 3721:3721 --rm \
  -e TRANSPORT_TYPE=stream_http \
  -e MCP_PORT=3721 \
  -e GITHUB_PERSONAL_ACCESS_TOKEN="..." \
  -e JENKINS_URL="..." \
  -e JENKINS_USER="..." \
  -e JENKINS_TOKEN="..." \
  -e ARTIFACTORY_URL="..." \
  -e ARTIFACTORY_IDENTITY_TOKEN="..." \
  devops-mcps
```

Replace `...` with your actual credentials.

## VSCode Integration

Configure the MCP server in VSCode's `settings.json`:

**Example (UVX with stdio):**

```json
"devops-mcps": {
  "type": "stdio",
  "command": "uvx",
  "args": ["run", "devops-mcps"],
  "env": {
    "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_...",
    "GITHUB_API_URL": "https://github.mycompany.com", // Optional for GHE
    "JENKINS_URL": "...",
    "JENKINS_USER": "...",
    "JENKINS_TOKEN": "...",
    "ARTIFACTORY_URL": "...",
    "ARTIFACTORY_IDENTITY_TOKEN": "cm..." // Or USERNAME/PASSWORD
  }
}
```

**Example (Docker with stream_http):**

Ensure the Docker container is running with stream_http enabled (see Docker section).

```json
{
  "type": "stream_http",
  "url": "http://127.0.0.1:3721/mcp", // Adjust if Docker host is remote or if MCP_PORT is set differently
  "env": {
    // Environment variables are set in the container,
    // but can be overridden here if needed.
    "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_..."
  }
}
```

Refer to the initial `README.md` sections for other transport/runner combinations (UVX/stream_http, Docker/stdio).

## Development

Set up your development environment:

```bash
# Install dependencies (using uv)
uv pip install -e ".[dev]"
# Or sync with lock file
# uv sync --dev
```

**Linting and Formatting (Ruff):**

```bash
# Check code style
uvx ruff check .

# Format code
uvx ruff format .
```

**Testing (Pytest):**

```bash
pytest --cov=src/devops_mcps --cov-report=html tests/
```

**Debugging with MCP Inspector:**

```bash
# Basic run
npx @modelcontextprotocol/inspector uvx run devops-mcps

# Run with specific environment variables
npx @modelcontextprotocol/inspector uvx run devops-mcps -e GITHUB_PERSONAL_ACCESS_TOKEN=... -e JENKINS_URL=... # Add other vars
```

**Checking for package dependencies outdated**

```bash
uv pip list --outdated
```

**Updating package dependencies**
```bash
uv lock --upgrade
```

## CI/CD

A GitHub Actions workflow (`.github/workflows/ci.yml`) handles:

1.  **Linting & Testing**: Runs Ruff and Pytest on pushes and pull requests.
2.  **Publishing**: Builds and publishes the Python package to PyPI and the Docker image to Docker Hub on pushes to the `main` branch.

**Required Repository Secrets:**

-   `PYPI_API_TOKEN`: PyPI token for package publishing.
-   `DOCKER_HUB_USERNAME`: Docker Hub username.
-   `DOCKER_HUB_TOKEN`: Docker Hub access token.

## Packaging and Publishing (Manual)

Ensure you have `build` and `twine` installed:

```bash
pip install -U build twine
```

1.  **Update Version**: Increment the version number in `pyproject.toml`.
2.  **Build**: `python -m build`
3.  **Upload**: `twine upload dist/*` (Requires `~/.pypirc` configuration or token input).

## Appendix: GitHub Search Query Syntax

Leverage GitHub's powerful search syntax within the MCP tools:

**Repository Search (`gh_search_repositories`):**

-   `in:name,description,readme`: Search specific fields.
    *Example: `fastapi in:name`*
-   `user:USERNAME` or `org:ORGNAME`: Scope search to a user/org.
    *Example: `user:tiangolo fastapi`*
-   `language:LANGUAGE`: Filter by language.
    *Example: `http client language:python`*
-   `stars:>N`, `forks:<N`, `created:YYYY-MM-DD`, `pushed:>YYYY-MM-DD`: Filter by metrics and dates.
    *Example: `language:javascript stars:>1000 pushed:>2024-01-01`*
-   `topic:TOPIC-NAME`: Filter by topic.
    *Example: `topic:docker topic:python`*
-   `license:LICENSE-KEYWORD`: Filter by license (e.g., `mit`, `apache-2.0`).
    *Example: `language:go license:mit`*

**Code Search (`gh_search_code`):**

-   `in:file,path`: Search file content (default) or path.
    *Example: `"import requests" in:file`*
-   `repo:OWNER/REPO`: Scope search to a specific repository.
    *Example: `"JenkinsAPIException" repo:your-org/your-repo`*
-   `language:LANGUAGE`: Filter by file language.
    *Example: `def main language:python`*
-   `path:PATH/TO/DIR`, `filename:FILENAME.EXT`, `extension:EXT`: Filter by path, filename, or extension.
    *Example: `"GithubException" path:src/devops_mcps extension:py`*

**References:**

-   [Searching on GitHub](https://docs.github.com/en/search-github/searching-on-github)
-   [Searching Code](https://docs.github.com/en/search-github/searching-on-github/searching-code)
-   [Searching Repositories](https://docs.github.com/en/search-github/searching-on-github/searching-for-repositories)

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.