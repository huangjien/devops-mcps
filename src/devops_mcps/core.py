# /Users/huangjien/workspace/devops-mcps/src/devops_mcps/core.py
import logging
import os
import sys
import argparse
from typing import List, Optional, Dict, Any, Union

# Third-party imports
from dotenv import load_dotenv
from importlib.metadata import version, PackageNotFoundError

# Import local modules after logging setup
from . import github, jenkins, azure
from . import artifactory

# MCP imports
from mcp.server.fastmcp import FastMCP

# Local imports
from .logger import setup_logging
from .prompts import PromptLoader

# Setup logging before importing github/jenkins
setup_logging()
logger = logging.getLogger(__name__)


# --- Environment Setup ---
load_dotenv()  # Load .env file

# --- Get Package Version ---
try:
  # Replace 'devops-mcps' if your actual distributable package name is different
  # This name usually comes from your pyproject.toml `[project] name`
  # or setup.py `name=` argument.
  package_version = version("devops-mcps")
  logger.info(f"Loaded package version: {package_version}")
except PackageNotFoundError:
  logger.warning(
    "Could not determine package version using importlib.metadata. "
    "Is the package installed correctly? Falling back to 'unknown'."
  )
  package_version = "?.?.?"  # Provide a fallback

# --- MCP Server Setup ---

mcp = FastMCP(
  f"DevOps MCP Server v{package_version} (Github & Jenkins)"
)


# --- Dynamic Prompts Loading ---
def load_and_register_prompts():
  """Load and register dynamic prompts from JSON file."""
  try:
    loader = PromptLoader()
    prompts = loader.load_prompts()

    if not prompts:
      logger.info("No dynamic prompts to register")
      return

    def create_prompt_handler(prompt_data):
      """Create a prompt handler function with proper closure."""

      async def prompt_handler(**kwargs):
        # Process template variables in the content
        content = prompt_data["template"]

        # Simple template variable replacement (Mustache-style)
        import re

        for key, value in kwargs.items():
          if value is not None:
            # Handle conditional blocks {{#key}}...{{/key}}
            conditional_pattern = r"{{{{#{key}}}}}(.*?){{{{/{key}}}}}".format(key=key)
            content = re.sub(conditional_pattern, r"\1", content, flags=re.DOTALL)

            # Handle negative conditional blocks {{^key}}...{{/key}}
            neg_conditional_pattern = r"{{{{\^{key}}}}}(.*?){{{{/{key}}}}}".format(
              key=key
            )
            content = re.sub(neg_conditional_pattern, "", content, flags=re.DOTALL)

            # Replace variable {{key}}
            content = content.replace("{{" + key + "}}", str(value))
          else:
            # Remove positive conditionals for None values
            conditional_pattern = r"{{{{#{key}}}}}(.*?){{{{/{key}}}}}".format(key=key)
            content = re.sub(conditional_pattern, "", content, flags=re.DOTALL)

            # Keep negative conditionals for None values
            neg_conditional_pattern = r"{{{{\^{key}}}}}(.*?){{{{/{key}}}}}".format(
              key=key
            )
            content = re.sub(neg_conditional_pattern, r"\1", content, flags=re.DOTALL)

        # Clean up any remaining template syntax
        import re

        content = re.sub(r"{{[^}]*}}", "", content)

        return {"content": content, "arguments": kwargs}

      return prompt_handler

    # Register each prompt with the MCP server
    for prompt_name, prompt_data in prompts.items():
      # Create argument schema for the prompt
      arguments = []
      if "arguments" in prompt_data:
        for arg in prompt_data["arguments"]:
          arg_def = {
            "name": arg["name"],
            "description": arg["description"],
            "required": arg.get("required", False),
          }
          arguments.append(arg_def)

      # Register the prompt with MCP using decorator approach
      handler = create_prompt_handler(prompt_data)

      # Use the @mcp.prompt decorator to register the prompt
      mcp.prompt(name=prompt_name, description=prompt_data["description"])(handler)

      logger.debug(f"Registered dynamic prompt: {prompt_name}")

    logger.info(f"Successfully registered {len(prompts)} dynamic prompts")

  except Exception as e:
    logger.error(f"Failed to load and register prompts: {e}")
    # Don't fail server startup if prompts fail to load
    pass


# --- MCP Tools (Wrappers around github.py functions) ---
# (No changes needed in the tool definitions themselves)
# Debug logs added previously will now be shown due to LOG_LEVEL change


# --- Azure Tools ---
@mcp.tool()
async def get_azure_subscriptions() -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Retrieve all Azure subscriptions accessible with current credentials.

  Returns:
      List of subscription dictionaries containing subscription details like:
      - id: Subscription ID
      - name: Subscription name
      - state: Subscription state (Enabled/Disabled)
      - tenantId: Azure tenant ID
      
      Example successful response:
      [
        {
          "id": "/subscriptions/12345678-1234-1234-1234-123456789012",
          "name": "Production Subscription",
          "state": "Enabled",
          "tenantId": "12345678-1234-1234-1234-123456789012"
        }
      ]

      Error response (Dict[str, str]):
      {
        "error": "Authentication failed: Invalid credentials or insufficient permissions"
      }

  Raises:
      AuthenticationError: If Azure credentials are invalid or missing
      PermissionError: If user lacks required subscription permissions
  """
  logger.debug("Executing get_azure_subscriptions")
  return azure.get_subscriptions()


@mcp.tool()
async def list_azure_vms(
  subscription_id: str,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """List all virtual machines (VMs) within a specific Azure subscription.

  Args:
      subscription_id (str): The Azure subscription ID where VMs are located.
        - Format: UUID format (e.g., "12345678-1234-1234-1234-123456789012")
        - Required: Yes
        - Example: "12345678-1234-1234-1234-123456789012"

  Returns:
      List of VM dictionaries containing VM details such as:
      - name: VM name
      - type: VM type/size
      - location: Azure region
      - powerState: Current power state (Running/Stopped/Deallocated)
      - osType: Operating system type (Windows/Linux)
      - resourceGroup: Resource group name

      Example successful response:
      [
        {
          "name": "my-vm-01",
          "type": "Standard_D2s_v3",
          "location": "eastus",
          "powerState": "Running",
          "osType": "Linux",
          "resourceGroup": "my-resource-group"
        }
      ]

      Error response (Dict[str, str]):
      {
        "error": "Subscription not found: Invalid subscription ID or access denied"
      }

  Raises:
      ValueError: If subscription_id is empty or invalid format
      PermissionError: If user lacks access to the specified subscription
  """
  logger.debug(f"Executing list_azure_vms for subscription: {subscription_id}")
  if not subscription_id:
    logger.error("Parameter 'subscription_id' cannot be empty")
    return {"error": "Parameter 'subscription_id' cannot be empty"}
  return azure.list_virtual_machines(subscription_id)


@mcp.tool()
async def list_aks_clusters(
  subscription_id: str,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """List all Azure Kubernetes Service (AKS) clusters within a specific Azure subscription.

  Args:
      subscription_id (str): The Azure subscription ID where AKS clusters are located.
        - Format: UUID format (e.g., "12345678-1234-1234-1234-123456789012")
        - Required: Yes
        - Example: "12345678-1234-1234-1234-123456789012"

  Returns:
      List of AKS cluster dictionaries containing cluster details such as:
      - name: Cluster name
      - location: Azure region
      - resourceGroup: Resource group name
      - kubernetesVersion: Kubernetes version
      - provisioningState: Current provisioning state
      - fqdn: Fully qualified domain name
      - nodeCount: Number of worker nodes
      - agentPoolProfiles: Agent pool configurations

      Example successful response:
      [
        {
          "name": "my-aks-cluster",
          "location": "westus2",
          "resourceGroup": "aks-rg",
          "kubernetesVersion": "1.27.3",
          "provisioningState": "Succeeded",
          "fqdn": "my-aks-cluster-12345678.hcp.westus2.azmk8s.io",
          "nodeCount": 3,
          "agentPoolProfiles": [{"name": "nodepool1", "count": 3, "vmSize": "Standard_D2s_v3"}]
        }
      ]

      Error response (Dict[str, str]):
      {
        "error": "Subscription not found: Invalid subscription ID or AKS access denied"
      }

  Raises:
      ValueError: If subscription_id is empty or invalid format
      PermissionError: If user lacks AKS cluster read permissions
      ResourceNotFoundError: If no AKS clusters exist in the subscription
  """
  logger.debug(f"Executing list_aks_clusters for subscription: {subscription_id}")
  if not subscription_id:
    logger.error("Parameter 'subscription_id' cannot be empty")
    return {"error": "Parameter 'subscription_id' cannot be empty"}
  return azure.list_aks_clusters(subscription_id)


@mcp.tool()
async def search_repositories(
  query: str,
  page: Optional[int] = 1,
  per_page: Optional[int] = 30,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Search for GitHub repositories using GitHub's advanced search syntax.

  Args:
      query (str): GitHub search query using advanced search syntax.
        - Required: Yes
        - Format: GitHub search query language
        - Examples:
          - "language:python stars:>1000" (Python repos with 1000+ stars)
          - "topic:machine-learning forks:>50" (ML repos with 50+ forks)
          - "user:github created:>2023-01-01" (GitHub user repos created in 2023)
          - "awesome in:name" (Repos with "awesome" in the name)
          - "size:>10000" (Repos larger than 10KB)

      page (int, optional): Page number for pagination.
        - Default: 1
        - Range: 1-100
        - Example: 2 (second page of results)

      per_page (int, optional): Number of results per page.
        - Default: 30
        - Maximum: 100
        - Example: 50 (50 results per page)

  Returns:
      List of repository dictionaries containing:
      - id: Repository ID
      - name: Repository name
      - full_name: Full repository name (owner/repo)
      - owner: Owner information
      - html_url: GitHub URL
      - description: Repository description
      - language: Primary programming language
      - stargazers_count: Number of stars
      - forks_count: Number of forks
      - watchers_count: Number of watchers
      - size: Repository size in KB
      - created_at: Creation timestamp
      - updated_at: Last update timestamp
      - pushed_at: Last push timestamp

      Example successful response:
      [
        {
          "id": 123456789,
          "name": "awesome-project",
          "full_name": "owner/awesome-project",
          "owner": {"login": "owner", "id": 987654321},
          "html_url": "https://github.com/owner/awesome-project",
          "description": "An awesome project description",
          "language": "Python",
          "stargazers_count": 1500,
          "forks_count": 300,
          "watchers_count": 75,
          "size": 2048,
          "created_at": "2023-01-15T10:30:00Z",
          "updated_at": "2023-12-01T14:20:00Z",
          "pushed_at": "2023-12-01T14:20:00Z"
        }
      ]

      Error response (Dict[str, str]):
      {
        "error": "Invalid search query: Query cannot be empty"
      }

  Raises:
      ValueError: If query is empty or invalid
      RateLimitExceededError: If GitHub API rate limit is exceeded
      SearchSyntaxError: If GitHub search syntax is invalid
  """
  logger.debug(f"Executing search_repositories with query: {query}")
  if not query:
    logger.error("Parameter 'query' cannot be empty")
    return {"error": "Parameter 'query' cannot be empty"}
  return github.gh_search_repositories(query=query)


@mcp.tool(
  name="github_get_current_user_info",
  description="Get detailed information about the currently authenticated GitHub user.",
)
async def github_get_current_user_info() -> Union[Dict[str, Any], Dict[str, str]]:
  """Get detailed information about the currently authenticated GitHub user.

  This tool requires valid GitHub authentication credentials (personal access token
  or OAuth token) to be configured in the environment or application settings.

  Returns:
      Dictionary containing comprehensive user information including:
      - login: GitHub username
      - id: GitHub user ID
      - node_id: GitHub node ID
      - avatar_url: Profile avatar URL
      - gravatar_id: Gravatar ID
      - url: GitHub API URL for user
      - html_url: GitHub profile URL
      - followers_url: Followers API URL
      - following_url: Following API URL
      - gists_url: Gists API URL
      - starred_url: Starred repositories API URL
      - subscriptions_url: Subscriptions API URL
      - organizations_url: Organizations API URL
      - repos_url: Repositories API URL
      - events_url: Events API URL
      - received_events_url: Received events API URL
      - type: User type ("User" or "Organization")
      - site_admin: Whether user is a GitHub site administrator
      - name: Full name
      - company: Company name
      - blog: Personal blog URL
      - location: Geographic location
      - email: Email address
      - hireable: Whether user is available for hire
      - bio: User biography
      - twitter_username: Twitter username
      - public_repos: Number of public repositories
      - public_gists: Number of public gists
      - followers: Number of followers
      - following: Number of users being followed
      - created_at: Account creation timestamp
      - updated_at: Last profile update timestamp
      - private_gists: Number of private gists
      - total_private_repos: Total private repositories
      - owned_private_repos: Owned private repositories
      - disk_usage: Disk usage in KB
      - collaborators: Number of collaborators
      - two_factor_authentication: Whether 2FA is enabled

      Example successful response:
      {
        "login": "octocat",
        "id": 1,
        "node_id": "MDQ6VXNlcjE=",
        "avatar_url": "https://github.com/images/error/octocat_happy.gif",
        "gravatar_id": "",
        "url": "https://api.github.com/users/octocat",
        "html_url": "https://github.com/octocat",
        "followers_url": "https://api.github.com/users/octocat/followers",
        "following_url": "https://api.github.com/users/octocat/following{/other_user}",
        "gists_url": "https://api.github.com/users/octocat/gists{/gist_id}",
        "starred_url": "https://api.github.com/users/octocat/starred{/owner}{/repo}",
        "subscriptions_url": "https://api.github.com/users/octocat/subscriptions",
        "organizations_url": "https://api.github.com/users/octocat/orgs",
        "repos_url": "https://api.github.com/users/octocat/repos",
        "events_url": "https://api.github.com/users/octocat/events{/privacy}",
        "received_events_url": "https://api.github.com/users/octocat/received_events",
        "type": "User",
        "site_admin": false,
        "name": "monalisa octocat",
        "company": "GitHub",
        "blog": "https://github.com/blog",
        "location": "San Francisco",
        "email": "octocat@github.com",
        "hireable": false,
        "bio": "There once was...",
        "twitter_username": "monatheoctocat",
        "public_repos": 2,
        "public_gists": 1,
        "followers": 20,
        "following": 0,
        "created_at": "2008-01-14T04:33:35Z",
        "updated_at": "2008-01-14T04:33:35Z",
        "private_gists": 81,
        "total_private_repos": 100,
        "owned_private_repos": 100,
        "disk_usage": 10000,
        "collaborators": 10,
        "two_factor_authentication": true
      }

      Error response (Dict[str, str]):
      {
        "error": "Authentication required: No valid GitHub credentials found"
      }

  Raises:
      AuthenticationError: If no valid GitHub credentials are configured
      RateLimitExceededError: If GitHub API rate limit is exceeded
      NetworkError: If connection to GitHub API fails
  """
  # Call the synchronous function from the github module directly
  # Note: This will block the event loop despite being in an async function.
  return (
    github.gh_get_current_user_info()
  )  # Removed try/except, error handling is in github.py


@mcp.tool()
async def get_file_contents(
  owner: str, repo: str, path: str, branch: Optional[str] = None
) -> Union[Dict[str, Any], Dict[str, str]]:
  """Get the contents of a file or directory from a GitHub repository.

  Args:
      owner (str): Repository owner (username or organization).
        - Required: Yes
        - Example: "microsoft", "google", "octocat"
        - Format: GitHub username or organization name

      repo (str): Repository name.
        - Required: Yes
        - Example: "vscode", "typescript", "Hello-World"
        - Format: Repository name (case-sensitive)

      path (str): Path to the file or directory within the repository.
        - Required: Yes
        - For files: Path relative to repository root (e.g., "src/main.py", "README.md")
        - For directories: Path ending with "/" (e.g., "src/", "docs/")
        - Root directory: Use "" or "/"
        - Examples: "src/utils/helpers.py", "docs/", ""

      branch (str, optional): Branch name to get contents from.
        - Default: Repository's default branch (usually "main" or "master")
        - Example: "main", "develop", "feature/new-ui"
        - Format: Branch name (case-sensitive)

  Returns:
      Dictionary containing file/directory contents with structure:

      For files:
      - type: "file"
      - name: File name
      - path: Full path within repository
      - sha: Git SHA of the file
      - size: File size in bytes
      - content: Base64-encoded file content (use base64.b64decode() to decode)
      - encoding: "base64"
      - download_url: Direct download URL
      - html_url: GitHub web URL
      - git_url: Git API URL

      For directories:
      - type: "dir"
      - name: Directory name
      - path: Full path within repository
      - sha: Git SHA of the directory
      - size: Always 0 for directories
      - download_url: null
      - html_url: GitHub web URL
      - git_url: Git API URL
      - entries: List of file/directory objects within this directory

      Example file response:
      {
        "type": "file",
        "name": "README.md",
        "path": "README.md",
        "sha": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
        "size": 1024,
        "content": "VGhpcyBpcyBhIFJFQURNRSBmaWxlIGNvbnRlbnQ=",
        "encoding": "base64",
        "download_url": "https://raw.githubusercontent.com/owner/repo/main/README.md",
        "html_url": "https://github.com/owner/repo/blob/main/README.md",
        "git_url": "https://api.github.com/repos/owner/repo/git/blobs/a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"
      }

      Example directory response:
      {
        "type": "dir",
        "name": "src",
        "path": "src",
        "sha": "b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1",
        "size": 0,
        "download_url": null,
        "html_url": "https://github.com/owner/repo/tree/main/src",
        "git_url": "https://api.github.com/repos/owner/repo/git/trees/b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1",
        "entries": [
          {"type": "file", "name": "main.py", "path": "src/main.py", "size": 2048},
          {"type": "dir", "name": "utils", "path": "src/utils", "size": 0}
        ]
      }

      Error response (Dict[str, str]):
      {
        "error": "File not found: The specified path does not exist in the repository"
      }

  Raises:
      ValueError: If owner, repo, or path parameters are empty
      FileNotFoundError: If the specified file or directory does not exist
      PermissionError: If user lacks read access to the repository
      RateLimitExceededError: If GitHub API rate limit is exceeded
  """
  logger.debug(f"Executing get_file_contents for {owner}/{repo}/{path}")
  if not owner:
    logger.error("Parameter 'owner' cannot be empty")
    return {"error": "Parameter 'owner' cannot be empty"}
  if not repo:
    logger.error("Parameter 'repo' cannot be empty")
    return {"error": "Parameter 'repo' cannot be empty"}
  if not path:
    logger.error("Parameter 'path' cannot be empty")
    return {"error": "Parameter 'path' cannot be empty"}
  return github.gh_get_file_contents(owner=owner, repo=repo, path=path, branch=branch)


@mcp.tool()
async def list_commits(
  owner: str,
  repo: str,
  sha: Optional[str] = None,
  page: Optional[int] = 1,
  per_page: Optional[int] = 30,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Get list of commits from a specific branch or commit SHA in a GitHub repository.

  Args:
      owner (str): Repository owner (username or organization).
        - Required: Yes
        - Example: "microsoft", "google", "octocat"
        - Format: GitHub username or organization name

      repo (str): Repository name.
        - Required: Yes
        - Example: "vscode", "typescript", "Hello-World"
        - Format: Repository name (case-sensitive)

      sha (str, optional): Branch name, tag name, or commit SHA.
        - Default: Repository's default branch (usually "main" or "master")
        - For branches: Use branch name (e.g., "main", "develop", "feature/new-ui")
        - For tags: Use tag name (e.g., "v1.0.0", "release-2023")
        - For specific commit: Use full commit SHA (40-character hash)
        - Example: "main", "develop", "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"

      page (int, optional): Page number for pagination.
        - Default: 1
        - Range: 1-100
        - Example: 2 (second page of commits)

      per_page (int, optional): Number of commits per page.
        - Default: 30
        - Maximum: 100
        - Example: 50 (50 commits per page)

  Returns:
      List of commit dictionaries containing:
      - sha: Commit SHA (40-character hash)
      - node_id: GitHub node ID
      - commit: Commit metadata including:
        - author: Author information (name, email, date)
        - committer: Committer information (name, email, date)
        - message: Commit message
        - tree: Tree SHA
        - url: Commit API URL
        - comment_count: Number of comments
      - url: Commit API URL
      - html_url: GitHub web URL
      - comments_url: Comments API URL
      - author: GitHub user information for author
      - committer: GitHub user information for committer
      - parents: List of parent commit SHAs
      - stats: Commit statistics (additions, deletions, total)
      - files: List of files modified in commit

      Example successful response:
      [
        {
          "sha": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
          "node_id": "MDY6Q29tbWl0MTIzNDU2Nzg5",
          "commit": {
            "author": {
              "name": "John Doe",
              "email": "john@example.com",
              "date": "2023-12-01T10:30:00Z"
            },
            "committer": {
              "name": "John Doe",
              "email": "john@example.com",
              "date": "2023-12-01T10:30:00Z"
            },
            "message": "Fix: Resolve authentication issue",
            "tree": {
              "sha": "b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1"
            },
            "url": "https://api.github.com/repos/owner/repo/git/commits/a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
            "comment_count": 3
          },
          "url": "https://api.github.com/repos/owner/repo/commits/a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
          "html_url": "https://github.com/owner/repo/commit/a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
          "comments_url": "https://api.github.com/repos/owner/repo/commits/a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0/comments",
          "author": {
            "login": "johndoe",
            "id": 123456789,
            "avatar_url": "https://avatars.githubusercontent.com/u/123456789?v=4"
          },
          "committer": {
            "login": "johndoe",
            "id": 123456789,
            "avatar_url": "https://avatars.githubusercontent.com/u/123456789?v=4"
          },
          "parents": [
            {"sha": "c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2"}
          ],
          "stats": {
            "additions": 15,
            "deletions": 8,
            "total": 23
          },
          "files": [
            {
              "filename": "src/auth.py",
              "additions": 15,
              "deletions": 8,
              "changes": 23,
              "status": "modified",
              "raw_url": "https://github.com/owner/repo/raw/a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0/src/auth.py"
            }
          ]
        }
      ]

      Error response (Dict[str, str]):
      {
        "error": "Branch not found: The specified branch does not exist in the repository"
      }

  Raises:
      ValueError: If owner or repo parameters are empty
      BranchNotFoundError: If the specified branch or SHA does not exist
      PermissionError: If user lacks read access to the repository
      RateLimitExceededError: If GitHub API rate limit is exceeded
  """
  logger.debug(f"Executing list_commits for {owner}/{repo}")
  if not owner:
    logger.error("Parameter 'owner' cannot be empty")
    return {"error": "Parameter 'owner' cannot be empty"}
  if not repo:
    logger.error("Parameter 'repo' cannot be empty")
    return {"error": "Parameter 'repo' cannot be empty"}
  # Use the sha parameter as the branch parameter for the GitHub API call
  return github.gh_list_commits(owner=owner, repo=repo, branch=sha)


@mcp.tool()
async def list_issues(
  owner: str,
  repo: str,
  state: Optional[str] = "open",
  labels: Optional[List[str]] = None,
  sort: Optional[str] = "created",
  direction: Optional[str] = "desc",
  page: Optional[int] = 1,
  per_page: Optional[int] = 30,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """List and filter issues in a GitHub repository with comprehensive filtering and sorting options.

  Args:
      owner (str): Repository owner (username or organization).
        - Required: Yes
        - Example: "microsoft", "google", "octocat"
        - Format: GitHub username or organization name

      repo (str): Repository name.
        - Required: Yes
        - Example: "vscode", "typescript", "Hello-World"
        - Format: Repository name (case-sensitive)

      state (str, optional): Filter by issue state.
        - Default: "open"
        - Valid values: "open", "closed", "all"
        - Example: "open" (only open issues), "closed" (only closed issues), "all" (all issues)

      labels (List[str], optional): Filter by one or more labels.
        - Default: None (no label filtering)
        - Format: List of label names
        - Multiple labels are treated as AND conditions
        - Example: ["bug", "high-priority"] (issues with both "bug" AND "high-priority" labels)
        - Note: Use GitHub's label search syntax for more complex filtering

      sort (str, optional): Sort results by specific criteria.
        - Default: "created"
        - Valid values: "created", "updated", "comments"
        - "created": Sort by creation date (newest first by default)
        - "updated": Sort by last update date
        - "comments": Sort by number of comments (most commented first by default)

      direction (str, optional): Sort direction.
        - Default: "desc" (descending)
        - Valid values: "asc", "desc"
        - "asc": Ascending order (oldest/least first)
        - "desc": Descending order (newest/most first)

      page (int, optional): Page number for pagination.
        - Default: 1
        - Range: 1-100
        - Example: 2 (second page of results)

      per_page (int, optional): Number of issues per page.
        - Default: 30
        - Maximum: 100
        - Example: 50 (50 issues per page)

  Returns:
      List of issue dictionaries containing:
      - id: Issue ID
      - node_id: GitHub node ID
      - url: API URL
      - repository_url: Repository API URL
      - labels_url: Labels API URL
      - comments_url: Comments API URL
      - events_url: Events API URL
      - html_url: GitHub web URL
      - number: Issue number
      - state: Issue state ("open", "closed")
      - title: Issue title
      - body: Issue description/content
      - user: User who created the issue
      - labels: List of label objects
      - assignee: Primary assignee
      - assignees: List of all assignees
      - milestone: Associated milestone
      - locked: Whether issue is locked
      - comments: Number of comments
      - pull_request: Pull request information (if applicable)
      - closed_at: Close timestamp (if closed)
      - created_at: Creation timestamp
      - updated_at: Last update timestamp
      - closed_by: User who closed the issue
      - author_association: Author's association with repository
      - active_lock_reason: Reason for lock (if locked)
      - draft: Whether issue is a draft (for pull requests)
      - reactions: Reaction counts

      Example successful response:
      [
        {
          "id": 123456789,
          "node_id": "MDU6SXNzdWUxMjM0NTY3ODk=",
          "url": "https://api.github.com/repos/owner/repo/issues/1",
          "repository_url": "https://api.github.com/repos/owner/repo",
          "labels_url": "https://api.github.com/repos/owner/repo/issues/1/labels",
          "comments_url": "https://api.github.com/repos/owner/repo/issues/1/comments",
          "events_url": "https://api.github.com/repos/owner/repo/issues/1/events",
          "html_url": "https://github.com/owner/repo/issues/1",
          "number": 1,
          "state": "open",
          "title": "Bug: Authentication fails with special characters",
          "body": "When users enter passwords with special characters like @ or #, authentication fails unexpectedly.",
          "user": {
            "login": "johndoe",
            "id": 987654321,
            "avatar_url": "https://avatars.githubusercontent.com/u/987654321?v=4"
          },
          "labels": [
            {
              "id": 123456,
              "node_id": "MDU6TGFiZWwxMjM0NTY=",
              "url": "https://api.github.com/repos/owner/repo/labels/bug",
              "name": "bug",
              "color": "d73a4a",
              "default": true,
              "description": "Something isn't working"
            },
            {
              "id": 654321,
              "node_id": "MDU6TGFiZWw2NTQzMjE=",
              "url": "https://api.github.com/repos/owner/repo/labels/high-priority",
              "name": "high-priority",
              "color": "b60205",
              "default": false,
              "description": "High priority issue"
            }
          ],
          "assignee": {
            "login": "janedoe",
            "id": 123456789,
            "avatar_url": "https://avatars.githubusercontent.com/u/123456789?v=4"
          },
          "assignees": [
            {
              "login": "janedoe",
              "id": 123456789,
              "avatar_url": "https://avatars.githubusercontent.com/u/123456789?v=4"
            }
          ],
          "milestone": null,
          "locked": false,
          "comments": 5,
          "pull_request": null,
          "closed_at": null,
          "created_at": "2023-12-01T10:30:00Z",
          "updated_at": "2023-12-02T14:20:00Z",
          "closed_by": null,
          "author_association": "CONTRIBUTOR",
          "active_lock_reason": null,
          "draft": false,
          "reactions": {
            "url": "https://api.github.com/repos/owner/repo/issues/1/reactions",
            "total_count": 3,
            "+1": 2,
            "-1": 0,
            "laugh": 1,
            "hooray": 0,
            "confused": 0,
            "heart": 0,
            "rocket": 0,
            "eyes": 0
          }
        }
      ]

      Error response (Dict[str, str]):
      {
        "error": "Repository not found: The specified repository does not exist or you don't have access"
      }

  Raises:
      ValueError: If owner or repo parameters are empty or invalid
      RepositoryNotFoundError: If the specified repository does not exist
      PermissionError: If user lacks read access to the repository
      RateLimitExceededError: If GitHub API rate limit is exceeded
      InvalidStateError: If invalid state parameter is provided
  """
  logger.debug(f"Executing list_issues for {owner}/{repo}, state: {state}")
  if not owner:
    logger.error("Parameter 'owner' cannot be empty")
    return {"error": "Parameter 'owner' cannot be empty"}
  if not repo:
    logger.error("Parameter 'repo' cannot be empty")
    return {"error": "Parameter 'repo' cannot be empty"}
  return github.gh_list_issues(
    owner=owner,
    repo=repo,
    state=state,
    labels=labels,
    sort=sort,
    direction=direction,
  )


@mcp.tool()
async def get_repository(
  owner: str, repo: str
) -> Union[Dict[str, Any], Dict[str, str]]:
  """Get comprehensive repository information and metadata from GitHub.

  Args:
      owner (str): Repository owner (username or organization).
        - Required: Yes
        - Example: "microsoft", "google", "octocat"
        - Format: GitHub username or organization name

      repo (str): Repository name.
        - Required: Yes
        - Example: "vscode", "typescript", "Hello-World"
        - Format: Repository name (case-sensitive)

  Returns:
      Repository information dictionary containing:
      - id: Repository ID
      - node_id: GitHub node ID
      - name: Repository name
      - full_name: Full repository name (owner/repo)
      - private: Whether repository is private
      - owner: Owner information (login, id, avatar_url, type)
      - html_url: GitHub web URL
      - description: Repository description
      - fork: Whether repository is a fork
      - url: API URL
      - forks_url: Forks API URL
      - keys_url: Keys API URL
      - collaborators_url: Collaborators API URL
      - teams_url: Teams API URL
      - hooks_url: Webhooks API URL
      - issue_events_url: Issue events API URL
      - events_url: Events API URL
      - assignees_url: Assignees API URL
      - branches_url: Branches API URL
      - tags_url: Tags API URL
      - blobs_url: Blobs API URL
      - git_tags_url: Git tags API URL
      - git_refs_url: Git refs API URL
      - trees_url: Trees API URL
      - statuses_url: Statuses API URL
      - languages_url: Languages API URL
      - stargazers_url: Stargazers API URL
      - contributors_url: Contributors API URL
      - subscribers_url: Subscribers API URL
      - subscription_url: Subscription API URL
      - commits_url: Commits API URL
      - git_commits_url: Git commits API URL
      - comments_url: Comments API URL
      - issue_comment_url: Issue comments API URL
      - contents_url: Contents API URL
      - compare_url: Compare API URL
      - merges_url: Merges API URL
      - archive_url: Archive API URL
      - downloads_url: Downloads API URL
      - issues_url: Issues API URL
      - pulls_url: Pull requests API URL
      - milestones_url: Milestones API URL
      - notifications_url: Notifications API URL
      - labels_url: Labels API URL
      - releases_url: Releases API URL
      - deployments_url: Deployments API URL
      - created_at: Creation timestamp
      - updated_at: Last update timestamp
      - pushed_at: Last push timestamp
      - git_url: Git URL
      - ssh_url: SSH URL
      - clone_url: Clone URL
      - svn_url: SVN URL
      - homepage: Homepage URL
      - size: Repository size in kilobytes
      - stargazers_count: Number of stars
      - watchers_count: Number of watchers
      - language: Primary programming language
      - has_issues: Whether issues are enabled
      - has_projects: Whether projects are enabled
      - has_downloads: Whether downloads are enabled
      - has_wiki: Whether wiki is enabled
      - has_pages: Whether GitHub Pages are enabled
      - has_discussions: Whether discussions are enabled
      - forks_count: Number of forks
      - mirror_url: Mirror URL (if applicable)
      - archived: Whether repository is archived
      - disabled: Whether repository is disabled
      - open_issues_count: Number of open issues
      - license: License information
      - allow_forking: Whether forking is allowed
      - is_template: Whether repository is a template
      - web_commit_signoff_required: Whether commit signoff is required
      - topics: List of repository topics
      - visibility: Repository visibility
      - default_branch: Default branch name
      - permissions: User permissions for the repository
      - temp_clone_token: Temporary clone token (if available)
      - allow_squash_merge: Whether squash merge is allowed
      - allow_merge_commit: Whether merge commits are allowed
      - allow_rebase_merge: Whether rebase merge is allowed
      - allow_auto_merge: Whether auto-merge is enabled
      - delete_branch_on_merge: Whether to delete branches on merge
      - allow_update_branch: Whether to allow branch updates
      - use_squash_pr_title_as_default: Whether to use PR title as default
      - squash_merge_commit_message: Squash merge commit message format
      - squash_merge_commit_title: Squash merge commit title format
      - merge_commit_message: Merge commit message format
      - merge_commit_title: Merge commit title format
      - network_count: Network count
      - subscribers_count: Number of subscribers

      Example successful response:
      {
        "id": 123456789,
        "node_id": "MDEwOlJlcG9zaXRvcnkxMjM0NTY3ODk=",
        "name": "vscode",
        "full_name": "microsoft/vscode",
        "private": false,
        "owner": {
          "login": "microsoft",
          "id": 6154722,
          "avatar_url": "https://avatars.githubusercontent.com/u/6154722?v=4",
          "type": "Organization"
        },
        "html_url": "https://github.com/microsoft/vscode",
        "description": "Visual Studio Code",
        "fork": false,
        "url": "https://api.github.com/repos/microsoft/vscode",
        "forks_url": "https://api.github.com/repos/microsoft/vscode/forks",
        "keys_url": "https://api.github.com/repos/microsoft/vscode/keys{/key_id}",
        "collaborators_url": "https://api.github.com/repos/microsoft/vscode/collaborators{/collaborator}",
        "teams_url": "https://api.github.com/repos/microsoft/vscode/teams",
        "hooks_url": "https://api.github.com/repos/microsoft/vscode/hooks",
        "issue_events_url": "https://api.github.com/repos/microsoft/vscode/issues/events{/number}",
        "events_url": "https://api.github.com/repos/microsoft/vscode/events",
        "assignees_url": "https://api.github.com/repos/microsoft/vscode/assignees{/user}",
        "branches_url": "https://api.github.com/repos/microsoft/vscode/branches{/branch}",
        "tags_url": "https://api.github.com/repos/microsoft/vscode/tags",
        "blobs_url": "https://api.github.com/repos/microsoft/vscode/git/blobs{/sha}",
        "git_tags_url": "https://api.github.com/repos/microsoft/vscode/git/tags{/sha}",
        "git_refs_url": "https://api.github.com/repos/microsoft/vscode/git/refs{/sha}",
        "trees_url": "https://api.github.com/repos/microsoft/vscode/git/trees{/sha}",
        "statuses_url": "https://api.github.com/repos/microsoft/vscode/statuses/{sha}",
        "languages_url": "https://api.github.com/repos/microsoft/vscode/languages",
        "stargazers_url": "https://api.github.com/repos/microsoft/vscode/stargazers",
        "contributors_url": "https://api.github.com/repos/microsoft/vscode/contributors",
        "subscribers_url": "https://api.github.com/repos/microsoft/vscode/subscribers",
        "subscription_url": "https://api.github.com/repos/microsoft/vscode/subscription",
        "commits_url": "https://api.github.com/repos/microsoft/vscode/commits{/sha}",
        "git_commits_url": "https://api.github.com/repos/microsoft/vscode/git/commits{/sha}",
        "comments_url": "https://api.github.com/repos/microsoft/vscode/comments{/number}",
        "issue_comment_url": "https://api.github.com/repos/microsoft/vscode/issues/comments{/number}",
        "contents_url": "https://api.github.com/repos/microsoft/vscode/contents/{+path}",
        "compare_url": "https://api.github.com/repos/microsoft/vscode/compare/{base}...{head}",
        "merges_url": "https://api.github.com/repos/microsoft/vscode/merges",
        "archive_url": "https://api.github.com/repos/microsoft/vscode/{archive_format}{/ref}",
        "downloads_url": "https://api.github.com/repos/microsoft/vscode/downloads",
        "issues_url": "https://api.github.com/repos/microsoft/vscode/issues{/number}",
        "pulls_url": "https://api.github.com/repos/microsoft/vscode/pulls{/number}",
        "milestones_url": "https://api.github.com/repos/microsoft/vscode/milestones{/number}",
        "notifications_url": "https://api.github.com/repos/microsoft/vscode/notifications{?since,all,participating}",
        "labels_url": "https://api.github.com/repos/microsoft/vscode/labels{/name}",
        "releases_url": "https://api.github.com/repos/microsoft/vscode/releases{/id}",
        "deployments_url": "https://api.github.com/repos/microsoft/vscode/deployments",
        "created_at": "2015-05-18T18:00:00Z",
        "updated_at": "2023-12-01T10:30:00Z",
        "pushed_at": "2023-12-02T14:20:00Z",
        "git_url": "git://github.com/microsoft/vscode.git",
        "ssh_url": "git@github.com:microsoft/vscode.git",
        "clone_url": "https://github.com/microsoft/vscode.git",
        "svn_url": "https://github.com/microsoft/vscode",
        "homepage": "https://code.visualstudio.com",
        "size": 102400,
        "stargazers_count": 158000,
        "watchers_count": 158000,
        "language": "TypeScript",
        "has_issues": true,
        "has_projects": true,
        "has_downloads": true,
        "has_wiki": false,
        "has_pages": false,
        "has_discussions": true,
        "forks_count": 28500,
        "mirror_url": null,
        "archived": false,
        "disabled": false,
        "open_issues_count": 7500,
        "license": {
          "key": "mit",
          "name": "MIT License",
          "spdx_id": "MIT",
          "url": "https://api.github.com/licenses/mit",
          "node_id": "MDc6TGljZW5zZTEz"
        },
        "allow_forking": true,
        "is_template": false,
        "web_commit_signoff_required": false,
        "topics": ["vscode", "editor", "typescript", "javascript", "development"],
        "visibility": "public",
        "default_branch": "main",
        "permissions": {
          "admin": false,
          "maintain": false,
          "push": false,
          "triage": false,
          "pull": true
        },
        "temp_clone_token": null,
        "allow_squash_merge": true,
        "allow_merge_commit": true,
        "allow_rebase_merge": true,
        "allow_auto_merge": false,
        "delete_branch_on_merge": false,
        "allow_update_branch": false,
        "use_squash_pr_title_as_default": false,
        "squash_merge_commit_message": "PR_BODY",
        "squash_merge_commit_title": "PR_TITLE",
        "merge_commit_message": "PR_TITLE",
        "merge_commit_title": "MERGE_MESSAGE",
        "network_count": 28500,
        "subscribers_count": 4200
      }

      Error response (Dict[str, str]):
      {
        "error": "Repository not found: The specified repository does not exist or you don't have access"
      }

  Raises:
      ValueError: If owner or repo parameters are empty or invalid
      RepositoryNotFoundError: If the specified repository does not exist
      PermissionError: If user lacks read access to the repository
      RateLimitExceededError: If GitHub API rate limit is exceeded
  """
  logger.debug(f"Executing get_repository for {owner}/{repo}")
  if not owner:
    logger.error("Parameter 'owner' cannot be empty")
    return {"error": "Parameter 'owner' cannot be empty"}
  if not repo:
    logger.error("Parameter 'repo' cannot be empty")
    return {"error": "Parameter 'repo' cannot be empty"}
  return github.gh_get_repository(owner=owner, repo=repo)


@mcp.tool()
async def search_code(
  query: str,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Search for code across GitHub repositories using GitHub's advanced code search syntax.

  Args:
      query (str): Search query using GitHub code search syntax.
        - Required: Yes
        - Example: "def main() language:python", "TODO user:github", "filename:Dockerfile org:microsoft"
        - Format: GitHub code search query with optional qualifiers:
          * language:LANG - Filter by programming language (python, javascript, java, etc.)
          * user:USERNAME - Search within a specific user's repositories
          * org:ORGNAME - Search within a specific organization's repositories
          * repo:OWNER/REPO - Search within a specific repository
          * filename:FILENAME - Search for files with specific names
          * path:PATH - Search within specific directories
          * extension:EXT - Search files with specific extensions
          * size:SIZE - Filter by file size (e.g., size:>1000)
          * created:YYYY-MM-DD - Filter by creation date
          * pushed:YYYY-MM-DD - Filter by last push date

  Returns:
      List of code search result dictionaries (first page) containing:
      - name: File name
      - path: File path within repository
      - sha: File SHA hash
      - url: GitHub API URL for the file
      - git_url: Git URL for the file
      - html_url: GitHub web URL for the file
      - repository: Repository information object
      - score: Search relevance score
      - text_matches: Array of text match objects showing context

      Example successful response (first result):
      [
        {
          "name": "main.py",
          "path": "src/main.py",
          "sha": "a1b2c3d4e5f678901234567890abcdef12345678",
          "url": "https://api.github.com/repos/example/repo/contents/src/main.py",
          "git_url": "https://api.github.com/repos/example/repo/git/blobs/a1b2c3d4e5f678901234567890abcdef12345678",
          "html_url": "https://github.com/example/repo/blob/main/src/main.py",
          "repository": {
            "id": 123456789,
            "node_id": "MDEwOlJlcG9zaXRvcnkxMjM0NTY3ODk=",
            "name": "repo",
            "full_name": "example/repo",
            "private": false,
            "owner": {
              "login": "example",
              "id": 987654321,
              "avatar_url": "https://avatars.githubusercontent.com/u/987654321?v=4",
              "type": "User"
            },
            "html_url": "https://github.com/example/repo",
            "description": "Example repository",
            "fork": false,
            "url": "https://api.github.com/repos/example/repo",
            "forks_url": "https://api.github.com/repos/example/repo/forks",
            "keys_url": "https://api.github.com/repos/example/repo/keys{/key_id}",
            "collaborators_url": "https://api.github.com/repos/example/repo/collaborators{/collaborator}",
            "teams_url": "https://api.github.com/repos/example/repo/teams",
            "hooks_url": "https://api.github.com/repos/example/repo/hooks",
            "issue_events_url": "https://api.github.com/repos/example/repo/issues/events{/number}",
            "events_url": "https://api.github.com/repos/example/repo/events",
            "assignees_url": "https://api.github.com/repos/example/repo/assignees{/user}",
            "branches_url": "https://api.github.com/repos/example/repo/branches{/branch}",
            "tags_url": "https://api.github.com/repos/example/repo/tags",
            "blobs_url": "https://api.github.com/repos/example/repo/git/blobs{/sha}",
            "git_tags_url": "https://api.github.com/repos/example/repo/git/tags{/sha}",
            "git_refs_url": "https://api.github.com/repos/example/repo/git/refs{/sha}",
            "trees_url": "https://api.github.com/repos/example/repo/git/trees{/sha}",
            "statuses_url": "https://api.github.com/repos/example/repo/statuses/{sha}",
            "languages_url": "https://api.github.com/repos/example/repo/languages",
            "stargazers_url": "https://api.github.com/repos/example/repo/stargazers",
            "contributors_url": "https://api.github.com/repos/example/repo/contributors",
            "subscribers_url": "https://api.github.com/repos/example/repo/subscribers",
            "subscription_url": "https://api.github.com/repos/example/repo/subscription",
            "commits_url": "https://api.github.com/repos/example/repo/commits{/sha}",
            "git_commits_url": "https://api.github.com/repos/example/repo/git/commits{/sha}",
            "comments_url": "https://api.github.com/repos/example/repo/comments{/number}",
            "issue_comment_url": "https://api.github.com/repos/example/repo/issues/comments{/number}",
            "contents_url": "https://api.github.com/repos/example/repo/contents/{+path}",
            "compare_url": "https://api.github.com/repos/example/repo/compare/{base}...{head}",
            "merges_url": "https://api.github.com/repos/example/repo/merges",
            "archive_url": "https://api.github.com/repos/example/repo/{archive_format}{/ref}",
            "downloads_url": "https://api.github.com/repos/example/repo/downloads",
            "issues_url": "https://api.github.com/repos/example/repo/issues{/number}",
            "pulls_url": "https://api.github.com/repos/example/repo/pulls{/number}",
            "milestones_url": "https://api.github.com/repos/example/repo/milestones{/number}",
            "notifications_url": "https://api.github.com/repos/example/repo/notifications{?since,all,participating}",
            "labels_url": "https://api.github.com/repos/example/repo/labels{/name}",
            "releases_url": "https://api.github.com/repos/example/repo/releases{/id}",
            "deployments_url": "https://api.github.com/repos/example/repo/deployments",
            "created_at": "2022-01-01T00:00:00Z",
            "updated_at": "2023-12-01T12:00:00Z",
            "pushed_at": "2023-12-02T15:30:00Z",
            "git_url": "git://github.com/example/repo.git",
            "ssh_url": "git@github.com:example/repo.git",
            "clone_url": "https://github.com/example/repo.git",
            "svn_url": "https://github.com/example/repo",
            "homepage": null,
            "size": 1024,
            "stargazers_count": 15,
            "watchers_count": 15,
            "language": "Python",
            "has_issues": true,
            "has_projects": true,
            "has_downloads": true,
            "has_wiki": true,
            "has_pages": false,
            "has_discussions": false,
            "forks_count": 3,
            "mirror_url": null,
            "archived": false,
            "disabled": false,
            "open_issues_count": 2,
            "license": null,
            "allow_forking": true,
            "is_template": false,
            "web_commit_signoff_required": false,
            "topics": [],
            "visibility": "public",
            "default_branch": "main",
            "permissions": {
              "admin": false,
              "maintain": false,
              "push": false,
              "triage": false,
              "pull": true
            }
          },
          "score": 1.0,
          "text_matches": [
            {
              "object_url": "https://api.github.com/repos/example/repo/contents/src/main.py",
              "object_type": "FileContent",
              "property": "content",
              "fragment": "def main():\n    print(\"Hello, World!\")\n\nif __name__ == \"__main__\":\n    main()",
              "matches": [
                {
                  "text": "def main()",
                  "indices": [0, 9],
                  "score": 1.0
                }
              ]
            }
          ]
        }
      ]

      Error response (Dict[str, str]):
      {
        "error": "Invalid search query: The query syntax is invalid or contains unsupported characters"
      }

      Example search queries:
      - "def main() language:python" - Find Python files containing 'def main()'
      - "TODO user:github" - Find TODO comments in GitHub's repositories
      - "filename:Dockerfile org:microsoft" - Find Dockerfiles in Microsoft organization
      - "console.log extension:js" - Find JavaScript files with console.log statements
      - "import React from language:javascript" - Find JavaScript files importing React
      - "#TODO language:python path:src" - Find Python TODO comments in src directory
      - "error handling size:>1000" - Find error handling code in files larger than 1KB

  Raises:
      ValueError: If search query is empty or invalid
      RateLimitExceededError: If GitHub API rate limit is exceeded
      InvalidSearchQueryError: If the search query syntax is invalid
      NetworkError: If there are network connectivity issues
  """
  logger.debug(f"Executing search_code with query: {query}")
  if not query:
    logger.error("Parameter 'query' cannot be empty")
    return {"error": "Parameter 'query' cannot be empty"}
  return github.gh_search_code(query=query)


# --- MCP Jenkins Tools (Wrappers around jenkins.py functions) ---
@mcp.tool()
async def get_jenkins_jobs() -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Retrieve all Jenkins jobs from the configured Jenkins server.

  Returns:
      List of job dictionaries containing comprehensive job information or an error dictionary.
      
      Each job dictionary includes:
      - name: Job name
      - url: Job URL
      - color: Build status color (blue, red, yellow, etc.)
      - fullname: Full job name including folder path
      - description: Job description
      - buildable: Whether the job can be built
      - inQueue: Whether the job is in the build queue
      - nextBuildNumber: Next available build number
      - concurrentBuild: Whether concurrent builds are enabled
      - healthReport: Array of health reports with scores and descriptions
      - property: Job properties and configurations
      - builds: Recent build information
      - firstBuild: First build information
      - lastBuild: Last build information
      - lastCompletedBuild: Last completed build information
      - lastFailedBuild: Last failed build information
      - lastStableBuild: Last stable build information
      - lastSuccessfulBuild: Last successful build information
      - lastUnstableBuild: Last unstable build information
      - lastUnsuccessfulBuild: Last unsuccessful build information

      Example successful response (first job):
      [
        {
          "name": "my-pipeline",
          "url": "https://jenkins.example.com/job/my-pipeline/",
          "color": "blue",
          "fullname": "my-pipeline",
          "description": "CI/CD pipeline for main application",
          "buildable": true,
          "inQueue": false,
          "nextBuildNumber": 42,
          "concurrentBuild": false,
          "healthReport": [
            {
              "description": "Build stability: 5 out of the last 5 builds failed.",
              "iconClassName": "icon-health-20to39",
              "iconUrl": "health-20to39.png",
              "score": 20
            }
          ],
          "property": [
            {
              "_class": "hudson.model.ParametersDefinitionProperty",
              "parameterDefinitions": [
                {
                  "_class": "hudson.model.StringParameterDefinition",
                  "defaultValue": "main",
                  "description": "Git branch to build",
                  "name": "BRANCH",
                  "type": "StringParameterDefinition"
                }
              ]
            }
          ],
          "builds": [
            {
              "number": 41,
              "url": "https://jenkins.example.com/job/my-pipeline/41/"
            },
            {
              "number": 40,
              "url": "https://jenkins.example.com/job/my-pipeline/40/"
            }
          ],
          "firstBuild": {
            "number": 1,
            "url": "https://jenkins.example.com/job/my-pipeline/1/"
          },
          "lastBuild": {
            "number": 41,
            "url": "https://jenkins.example.com/job/my-pipeline/41/"
          },
          "lastCompletedBuild": {
            "number": 41,
            "url": "https://jenkins.example.com/job/my-pipeline/41/"
          },
          "lastFailedBuild": {
            "number": 39,
            "url": "https://jenkins.example.com/job/my-pipeline/39/"
          },
          "lastStableBuild": {
            "number": 38,
            "url": "https://jenkins.example.com/job/my-pipeline/38/"
          },
          "lastSuccessfulBuild": {
            "number": 38,
            "url": "https://jenkins.example.com/job/my-pipeline/38/"
          },
          "lastUnstableBuild": null,
          "lastUnsuccessfulBuild": {
            "number": 41,
            "url": "https://jenkins.example.com/job/my-pipeline/41/"
          }
        }
      ]

      Error response (Dict[str, str]):
      {
        "error": "Jenkins connection failed: Unable to connect to Jenkins server at https://jenkins.example.com"
      }

      Common error scenarios:
      - Jenkins server unavailable or unreachable
      - Authentication failure (invalid credentials)
      - Permission denied for accessing jobs
      - Network connectivity issues

  Raises:
      JenkinsConnectionError: If unable to connect to Jenkins server
      AuthenticationError: If Jenkins credentials are invalid or missing
      PermissionError: If user lacks permission to view jobs
      NetworkError: If there are network connectivity issues
  """
  logger.debug("Executing get_jenkins_jobs")
  return jenkins.jenkins_get_jobs()


@mcp.tool()
async def get_jenkins_build_log(
  job_name: str, build_number: int
) -> Union[str, Dict[str, str]]:
  """Retrieve the build log for a specific Jenkins job and build number.

  Args:
      job_name (str): Name of the Jenkins job.
        - Required: Yes
        - Example: "my-pipeline", "backend-tests", "deploy-production"
        - Format: Exact job name as it appears in Jenkins
        
      build_number (int): Build number to retrieve.
        - Required: Yes
        - Special values: 0 or negative numbers will retrieve the last build
        - Example: 42 (specific build), 0 (last build), -1 (last build)
        - Range: Positive integers for specific builds, 0/-1 for latest

  Returns:
      The last 10KB of the build log content (str) or an error dictionary.
      
      Note: For performance and memory considerations, only the last 10KB (10,240 characters) 
      of the build log is returned. For full logs, use Jenkins web interface directly.

      Error response (Dict[str, str]):
      {
        "error": "Build not found: Job 'my-pipeline' build #999 does not exist"
      }

      Common error scenarios:
      - Job does not exist
      - Build number does not exist for the specified job
      - Jenkins server unavailable or unreachable
      - Authentication failure
      - Permission denied for accessing build logs
      - Network connectivity issues

      Example usage scenarios:
      - get_jenkins_build_log("my-pipeline", 42) - Get log for build #42
      - get_jenkins_build_log("backend-tests", 0) - Get log for latest build
      - get_jenkins_build_log("deploy-production", -1) - Get log for latest build

  Raises:
      ValueError: If job_name is empty or build_number is None
      JenkinsConnectionError: If unable to connect to Jenkins server
      BuildNotFoundError: If the specified build does not exist
      PermissionError: If user lacks permission to view build logs
      NetworkError: If there are network connectivity issues
  """
  logger.debug(
    f"Executing get_jenkins_build_log for job: {job_name}, build: {build_number}"
  )
  if not job_name:
    logger.error("Parameter job_name cannot be empty")
    return {"error": "Parameter job_name cannot be empty"}
  if build_number is None:
    logger.error("Parameter build_number cannot be empty")
    return {"error": "Parameter build_number cannot be empty"}
  return jenkins.jenkins_get_build_log(job_name=job_name, build_number=build_number)


@mcp.tool()
async def get_all_jenkins_views() -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Retrieve all views configured in the Jenkins server.

  Returns:
      A list of view dictionaries or an error dictionary.
      
      Each view dictionary contains:
        - name (str): The name of the view
        - url (str): The URL to access the view in Jenkins web interface
        - description (str, optional): Description of the view (if configured)
        - jobs (List[str], optional): List of job names included in this view
        - type (str): Type of view (e.g., 'list', 'dashboard', 'my', 'all')

      Example successful response (List[Dict[str, Any]]):
      [
        {
          "name": "All",
          "url": "https://jenkins.example.com/view/All/",
          "description": "All jobs in this Jenkins instance",
          "jobs": ["backend-pipeline", "frontend-pipeline", "deploy-production"],
          "type": "list"
        },
        {
          "name": "Dashboard",
          "url": "https://jenkins.example.com/view/Dashboard/",
          "description": "Main dashboard view with build status",
          "jobs": ["backend-pipeline", "frontend-pipeline"],
          "type": "dashboard"
        },
        {
          "name": "My-View",
          "url": "https://jenkins.example.com/view/My-View/",
          "description": "Personal view with frequently accessed jobs",
          "jobs": ["backend-pipeline"],
          "type": "list"
        }
      ]

      Error response (Dict[str, str]):
      {
        "error": "Unable to connect to Jenkins server: Connection refused"
      }

      Common error scenarios:
      - Jenkins server unavailable or unreachable
      - Authentication failure (invalid credentials)
      - Permission denied for accessing views
      - Network connectivity issues

      Example usage scenarios:
      - get_all_jenkins_views() - Retrieve all configured views
      - Filter views by type or name for specific dashboard configurations
      - Get job listings organized by view structure

  Raises:
      JenkinsConnectionError: If unable to connect to Jenkins server
      AuthenticationError: If Jenkins credentials are invalid or missing
      PermissionError: If user lacks permission to access views
      NetworkError: If there are network connectivity issues
  """
  logger.debug("Executing get_all_jenkins_views")
  return jenkins.jenkins_get_all_views()


@mcp.tool()
async def get_recent_failed_jenkins_builds(
  hours_ago: int = 8,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Retrieve Jenkins builds that failed within the specified time period.

  Args:
      hours_ago (int, optional): Number of hours to look back for failed builds.
        - Required: No
        - Default: 8 hours
        - Range: 1-168 hours (1 week maximum for performance reasons)
        - Example: 24 (last 24 hours), 8 (last 8 hours), 1 (last hour)
        - Note: Values outside 1-168 range will be clamped to valid range

  Returns:
      A list of failed build dictionaries or an error dictionary.
      
      Each build dictionary contains:
        - job_name (str): Name of the Jenkins job
        - build_number (int): Build number
        - status (str): Build status (e.g., 'FAILURE', 'ABORTED', 'UNSTABLE')
        - timestamp_utc (str): ISO 8601 timestamp of when the build finished
        - url (str): URL to access the build details in Jenkins web interface
        - duration (int, optional): Build duration in milliseconds
        - cause (str, optional): Reason for build failure if available

      Example successful response (List[Dict[str, Any]]):
      [
        {
          "job_name": "backend-pipeline",
          "build_number": 123,
          "status": "FAILURE",
          "timestamp_utc": "2023-12-15T10:30:45Z",
          "url": "https://jenkins.example.com/job/backend-pipeline/123/",
          "duration": 15678,
          "cause": "Test failures in backend unit tests"
        },
        {
          "job_name": "frontend-deploy",
          "build_number": 45,
          "status": "FAILURE",
          "timestamp_utc": "2023-12-15T09:15:22Z",
          "url": "https://jenkins.example.com/job/frontend-deploy/45/",
          "duration": 8923,
          "cause": "Deployment timeout to production environment"
        }
      ]

      Error response (Dict[str, str]):
      {
        "error": "Unable to connect to Jenkins server: Connection refused"
      }

      Common error scenarios:
      - Jenkins server unavailable or unreachable
      - Authentication failure (invalid credentials)
      - Permission denied for accessing build information
      - Network connectivity issues
      - No failed builds found in the specified time period (returns empty list)

      Example usage scenarios:
      - get_recent_failed_jenkins_builds(24) - Check failures in last 24 hours
      - get_recent_failed_jenkins_builds(1) - Check failures in last hour
      - get_recent_failed_jenkins_builds() - Default 8-hour lookback
      - Monitor deployment pipeline failures for immediate investigation

  Raises:
      JenkinsConnectionError: If unable to connect to Jenkins server
      AuthenticationError: If Jenkins credentials are invalid or missing
      PermissionError: If user lacks permission to access build information
      NetworkError: If there are network connectivity issues
  """
  # --- Use the hours_ago variable in the log ---
  logger.debug(f"Executing get_recent_failed_jenkins_builds for last {hours_ago} hours")
  # --- Pass the hours_ago parameter ---
  return jenkins.jenkins_get_recent_failed_builds(hours_ago=hours_ago)


# --- End new MCP tool ---


@mcp.tool()
async def clear_cache() -> Dict[str, str]:
  """Clear all cached data from the in-memory cache.

  This tool clears the application's internal cache, which may include:
  - API response caching for GitHub, Jenkins, Azure, and Artifactory operations
  - Authentication tokens and session data
  - Configuration data and connection settings
  - Temporary data storage for ongoing operations

  Returns:
      A dictionary indicating the success status of the cache clearing operation.
      
      Example successful response:
      {
        "status": "success", 
        "message": "Cache cleared successfully",
        "cache_size_before": 1024,
        "cache_size_after": 0
      }

      Error response:
      {
        "status": "error",
        "message": "Failed to clear cache: Cache manager not initialized"
      }

  Common usage scenarios:
  - Clear stale or outdated cached data after configuration changes
  - Force fresh data retrieval when cached results are suspected to be incorrect
  - Free up memory by clearing large cached responses
  - Reset authentication state when switching between different environments
  - Troubleshoot caching-related issues by forcing cache refresh

  Note: Clearing the cache may result in:
  - Temporary performance degradation as fresh data is retrieved
  - Increased API calls to external services
  - Loss of temporary session data and authentication tokens

  Example usage scenarios:
  - clear_cache() - Clear all cached data
  - Use after changing Jenkins server configuration to force fresh connection
  - Use after updating GitHub credentials to clear cached authentication tokens
  - Use when troubleshooting inconsistent API responses

  Raises:
      CacheError: If cache manager encounters issues during clearing operation
      InitializationError: If cache system is not properly initialized
  """
  logger.debug("Executing clear_cache")
  try:
    from .cache import cache_manager

    cache_manager.clear()
    logger.info("Cache cleared successfully")
    return {"status": "success", "message": "Cache cleared successfully"}
  except Exception as e:
    logger.error(f"Failed to clear cache: {e}")
    return {"status": "error", "message": f"Failed to clear cache: {e}"}


# --- Main Execution Logic ---
# (No changes needed in main() or main_stream_http())


def main():
  """Entry point for the CLI."""
  # Ensure environment variables are loaded before initializing the github client
  github.initialize_github_client(force=True)

  # Load and register dynamic prompts
  load_and_register_prompts()

  parser = argparse.ArgumentParser(
    description="DevOps MCP Server (PyGithub - Raw Output)"
  )
  parser.add_argument(
    "--transport",
    choices=["stdio", "stream_http"],
    default="stdio",
    help="Transport type (stdio or stream_http)",
  )

  args = parser.parse_args()

  # Check if the GitHub client initialized successfully (accessing the global 'g' from the imported module)
  if github.g is None:
    # Initialization logs errors/warnings, but we might want to prevent startup
    # Check the environment variable directly instead of the cached value
    current_github_token = os.environ.get("GITHUB_TOKEN")
    if current_github_token:
      logger.error(  # This will now go to file & console
        "GitHub client failed to initialize despite token being present. Check logs. Exiting."
      )
      sys.exit(1)
    else:
      # Allow running without auth, but tools will return errors if called
      logger.warning(  # This will now go to file & console
        "Running without GitHub authentication. GitHub tools will fail if used."
      )
  # Check if the Jenkins client initialized successfully
  if jenkins.j is None:
    if jenkins.JENKINS_URL and jenkins.JENKINS_USER and jenkins.JENKINS_TOKEN:
      logger.error(  # This will now go to file & console
        "Jenkins client failed to initialize despite credentials being present. Check logs. Exiting."
      )
      sys.exit(1)
    else:
      logger.warning(  # This will now go to file & console
        "Running without Jenkins authentication. Jenkins tools will fail if used."
      )
  logger.info(
    f"Starting MCP server with {args.transport} transport..."
  )  # This will now go to file & console

  if args.transport == "stream_http":
    port = int(os.getenv("MCP_PORT", "3721"))
    mcp.run(transport="http", host="127.0.0.1", port=port, path="/mcp")
  else:
    mcp.run(transport=args.transport)


def main_stream_http():
  """Run the MCP server with stream_http transport."""
  if "--transport" not in sys.argv:
    sys.argv.extend(["--transport", "stream_http"])
  elif "stream_http" not in sys.argv:
    try:
      idx = sys.argv.index("--transport")
      if idx + 1 < len(sys.argv):
        sys.argv[idx + 1] = "stream_http"
      else:
        sys.argv.append("stream_http")
    except ValueError:
      sys.argv.extend(["--transport", "stream_http"])

  main()


if __name__ == "__main__":
  main()


@mcp.tool()
async def list_artifactory_items(
  repository: str, path: str = "/"
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """List items under a given repository and path in Artifactory.

  Args:
      repository: The Artifactory repository name (e.g., "libs-release-local", "docker-local", "npm-local").
      path: The path within the repository (default: "/"). Use "/" for repository root.

  Returns:
      List of item dictionaries with the following structure:
      [
        {
          "uri": "string",          # Full URI to the item
          "repo": "string",         # Repository name
          "path": "string",         # Path within repository
          "name": "string",         # Item name
          "type": "string",         # Item type ("folder" or "file")
          "size": int,             # File size in bytes (for files)
          "created": "string",     # Creation timestamp
          "created_by": "string",  # User who created the item
          "modified": "string",    # Last modification timestamp
          "modified_by": "string", # User who last modified the item
          "last_updated": "string" # Last update timestamp
        }
      ]
      or an error dictionary with status and message.

  Examples of repository paths:
  - "/" - Repository root
  - "com/example" - Specific package path
  - "org/company/project" - Organizational path
  - "docker/images/nginx" - Docker image repository path
  - "npm/@scope/package" - NPM scoped package path

  Common repository types and examples:
  - Maven repositories: "libs-release-local", "libs-snapshot-local"
  - Docker repositories: "docker-local", "docker-remote"
  - NPM repositories: "npm-local", "npm-remote"
  - Generic repositories: "generic-local", "generic-remote"

  Successful response example:
  {
    "status": "success",
    "items": [
      {
        "uri": "http://artifactory.example.com/artifactory/libs-release-local/com/example/",
        "repo": "libs-release-local",
        "path": "com/example",
        "name": "example",
        "type": "folder",
        "size": 0,
        "created": "2023-01-15T10:30:00.000Z",
        "created_by": "admin",
        "modified": "2023-01-15T10:30:00.000Z",
        "modified_by": "admin",
        "last_updated": "2023-01-15T10:30:00.000Z"
      }
    ]
  }

  Error response example:
  {
    "status": "error",
    "message": "Repository 'invalid-repo' not found or access denied"
  }

  Common error scenarios:
  - Repository does not exist or access is denied
  - Invalid path format or malformed repository name
  - Network connectivity issues to Artifactory server
  - Authentication or permission errors
  - Path does not exist within the repository

  Raises:
      ValueError: If repository parameter is empty or invalid
      ArtifactoryConnectionError: If unable to connect to Artifactory server
      AuthenticationError: If authentication fails
      PermissionError: If user lacks permissions to access the repository
      NetworkError: If network connectivity issues occur
  """
  logger.debug(f"Executing list_artifactory_items for {repository}/{path}")
  if not repository:
    logger.error("Parameter 'repository' cannot be empty")
    return {"error": "Parameter 'repository' cannot be empty"}
  return artifactory.artifactory_list_items(repository=repository, path=path)


@mcp.tool()
async def search_artifactory_items(
  query: str, repositories: Optional[List[str]] = None
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Search for items across multiple repositories in Artifactory using AQL (Artifactory Query Language).

  Args:
      query: The AQL search query. Supports complex filtering and searching capabilities.
      repositories: Optional list of repository names to search in (if None, searches all accessible repositories).

  Returns:
      List of search result dictionaries with the following structure:
      [
        {
          "repo": "string",         # Repository name
          "path": "string",         # Path within repository
          "name": "string",         # Item name
          "type": "string",         # Item type ("folder" or "file")
          "size": int,             # File size in bytes
          "created": "string",     # Creation timestamp
          "created_by": "string",  # User who created the item
          "modified": "string",    # Last modification timestamp
          "modified_by": "string", # User who last modified the item
          "last_updated": "string", # Last update timestamp
          "sha1": "string",        # SHA1 checksum
          "sha256": "string",      # SHA256 checksum
          "md5": "string"          # MD5 checksum
        }
      ]
      or an error dictionary with status and message.

  AQL Query Examples:
  - Find all files: "items.find()"
  - Find files by name: "items.find({\"name\":{\"$eq\":\"*.jar\"}})"
  - Find files by repository: "items.find({\"repo\":{\"$eq\":\"libs-release-local\"}})"
  - Find files by path: "items.find({\"path\":{\"$match\":\"com/example/*\"}})"
  - Find files by size: "items.find({\"size\":{\"$gt\":1048576}})"  # >1MB
  - Find files by creation date: "items.find({\"created\":{\"$before\":\"2023-01-01T00:00:00.000Z\"}})"
  - Find files by checksum: "items.find({\"sha1\":{\"$eq\":\"abc123...\"}})"
  - Find files with multiple criteria: "items.find({\"$and\":[{\"repo\":\"libs-release-local\"},{\"name\":{\"$match\":\"*.jar\"}}]})"

  Common AQL Operators:
  - $eq: Equal to
  - $ne: Not equal to
  - $gt: Greater than
  - $gte: Greater than or equal to
  - $lt: Less than
  - $lte: Less than or equal to
  - $match: Pattern matching
  - $nmatch: Not matching pattern
  - $and: Logical AND
  - $or: Logical OR
  - $not: Logical NOT

  Repository examples for the repositories parameter:
  - ["libs-release-local", "libs-snapshot-local"] - Search specific Maven repositories
  - ["docker-local", "docker-remote"] - Search Docker repositories
  - ["npm-local", "npm-remote"] - Search NPM repositories
  - None - Search all accessible repositories

  Successful response example:
  {
    "status": "success",
    "results": [
      {
        "repo": "libs-release-local",
        "path": "com/example/app",
        "name": "app-1.0.0.jar",
        "type": "file",
        "size": 5242880,
        "created": "2023-01-15T10:30:00.000Z",
        "created_by": "jenkins",
        "modified": "2023-01-15T10:30:00.000Z",
        "modified_by": "jenkins",
        "last_updated": "2023-01-15T10:30:00.000Z",
        "sha1": "abc123def456...",
        "sha256": "sha256hash...",
        "md5": "md5hash..."
      }
    ]
  }

  Error response example:
  {
    "status": "error",
    "message": "Invalid AQL query syntax: items.find({\"name\":{\"$invalid\":\"*.jar\"}})"
  }

  Common error scenarios:
  - Invalid AQL query syntax
  - Repository not found or access denied
  - Network connectivity issues to Artifactory server
  - Authentication or permission errors
  - Timeout during complex search operations
  - Invalid repository names in repositories list

  Raises:
      ValueError: If query parameter is empty or invalid
      ArtifactoryConnectionError: If unable to connect to Artifactory server
      AuthenticationError: If authentication fails
      PermissionError: If user lacks permissions to perform searches
      NetworkError: If network connectivity issues occur
      QuerySyntaxError: If AQL query syntax is invalid
  """
  logger.debug(f"Executing search_artifactory_items with query: {query}")
  if not query:
    logger.error("Parameter 'query' cannot be empty")
    return {"error": "Parameter 'query' cannot be empty"}
  return artifactory.artifactory_search_items(query=query, repositories=repositories)


@mcp.tool()
async def get_artifactory_item_info(
  repository: str, path: str
) -> Union[Dict[str, Any], Dict[str, str]]:
  """Get detailed information about a specific item in Artifactory.

  Args:
      repository: The Artifactory repository name (e.g., "libs-release-local", "docker-local", "npm-local").
      path: The full path to the item within the repository (e.g., "com/example/app/1.0.0/app-1.0.0.jar").

  Returns:
      Detailed item information dictionary with the following structure:
      {
        "repo": "string",               # Repository name
        "path": "string",               # Path within repository
        "name": "string",               # Item name
        "type": "string",               # Item type ("folder" or "file")
        "size": int,                   # File size in bytes (for files)
        "created": "string",           # Creation timestamp (ISO 8601)
        "created_by": "string",        # User who created the item
        "modified": "string",           # Last modification timestamp
        "modified_by": "string",       # User who last modified the item
        "last_updated": "string",       # Last update timestamp
        "last_downloaded": "string",    # Last download timestamp (if applicable)
        "download_count": int,         # Number of times downloaded
        "sha1": "string",              # SHA1 checksum
        "sha256": "string",            # SHA256 checksum
        "md5": "string",               # MD5 checksum
        "mime_type": "string",         # MIME type (for files)
        "uri": "string",               # Full URI to the item
        "download_uri": "string",      # Direct download URI
        "original_md5": "string",      # Original MD5 (for checksum verified files)
        "original_sha1": "string",     # Original SHA1 (for checksum verified files)
        "original_sha256": "string",    # Original SHA256 (for checksum verified files)
        "properties": {                # Custom properties attached to the item
          "property_name": "property_value",
          "build.name": "project-name",
          "build.number": "123"
        },
        "stats": {                     # Usage statistics
          "downloads": int,           # Total downloads
          "last_downloaded": "string", # Last download timestamp
          "last_downloaded_by": "string" # User who last downloaded
        }
      }
      or an error dictionary with status and message.

  Path examples:
  - Maven artifact: "com/example/app/1.0.0/app-1.0.0.jar"
  - Docker image: "nginx/latest/manifest.json"
  - NPM package: "@scope/package/1.0.0/package.tgz"
  - Generic file: "documents/user-guide.pdf"
  - Folder: "com/example/app/"

  Repository examples:
  - Maven: "libs-release-local", "libs-snapshot-local"
  - Docker: "docker-local", "docker-remote"
  - NPM: "npm-local", "npm-remote"
  - Generic: "generic-local", "generic-remote"

  Successful response example:
  {
    "status": "success",
    "item": {
      "repo": "libs-release-local",
      "path": "com/example/app/1.0.0",
      "name": "app-1.0.0.jar",
      "type": "file",
      "size": 5242880,
      "created": "2023-01-15T10:30:00.000Z",
      "created_by": "jenkins",
      "modified": "2023-01-15T10:30:00.000Z",
      "modified_by": "jenkins",
      "last_updated": "2023-01-15T10:30:00.000Z",
      "last_downloaded": "2023-01-20T14:25:00.000Z",
      "download_count": 15,
      "sha1": "abc123def4567890...",
      "sha256": "sha256hashvalue...",
      "md5": "md5hashvalue...",
      "mime_type": "application/java-archive",
      "uri": "http://artifactory.example.com/artifactory/libs-release-local/com/example/app/1.0.0/app-1.0.0.jar",
      "download_uri": "http://artifactory.example.com/artifactory/libs-release-local/com/example/app/1.0.0/app-1.0.0.jar",
      "properties": {
        "build.name": "example-app",
        "build.number": "123",
        "version": "1.0.0",
        "team": "backend"
      },
      "stats": {
        "downloads": 15,
        "last_downloaded": "2023-01-20T14:25:00.000Z",
        "last_downloaded_by": "developer@example.com"
      }
    }
  }

  Error response example:
  {
    "status": "error",
    "message": "Item not found: Repository 'invalid-repo' or path 'nonexistent/path.jar' does not exist"
  }

  Common error scenarios:
  - Item not found in the specified repository and path
  - Repository does not exist or access is denied
  - Invalid path format or malformed repository name
  - Network connectivity issues to Artifactory server
  - Authentication or permission errors
  - Item is a folder when file metadata was expected (or vice versa)

  Raises:
      ValueError: If repository or path parameters are empty or invalid
      ArtifactoryConnectionError: If unable to connect to Artifactory server
      AuthenticationError: If authentication fails
      PermissionError: If user lacks permissions to access the item
      NetworkError: If network connectivity issues occur
      ItemNotFoundError: If the specified item does not exist
  """
  logger.debug(f"Executing get_artifactory_item_info for {repository}/{path}")
  if not repository:
    logger.error("Parameter 'repository' cannot be empty")
    return {"error": "Parameter 'repository' cannot be empty"}
  if not path:
    logger.error("Parameter 'path' cannot be empty")
    return {"error": "Parameter 'path' cannot be empty"}
  return artifactory.artifactory_get_item_info(repository=repository, path=path)


@mcp.tool()
async def get_github_issue_content(owner: str, repo: str, issue_number: int) -> dict:
  """Get comprehensive GitHub issue content including metadata, comments, assignees, labels, and timeline events.

  Args:
      owner: Repository owner username or organization (e.g., "microsoft", "google", "apache").
      repo: Repository name (e.g., "vscode", "chromium", "kafka").
      issue_number: GitHub issue or pull request number (must be a positive integer).

  Returns:
      Detailed issue information dictionary with the following structure:
      {
        "status": "success",
        "issue": {
          "number": int,                   # Issue number
          "title": "string",              # Issue title
          "body": "string",               # Issue body/description
          "state": "string",              # Issue state ("open", "closed")
          "created_at": "string",         # Creation timestamp (ISO 8601)
          "updated_at": "string",         # Last update timestamp
          "closed_at": "string",          # Close timestamp (if closed)
          "html_url": "string",           # URL to view issue in browser
          "user": {                       # Issue creator information
            "login": "string",           # Username
            "id": int,                   # User ID
            "avatar_url": "string",      # Avatar URL
            "html_url": "string"         # Profile URL
          },
          "assignees": [                  # List of assigned users
            {
              "login": "string",
              "id": int,
              "avatar_url": "string",
              "html_url": "string"
            }
          ],
          "labels": [                     # List of labels
            {
              "id": int,                 # Label ID
              "name": "string",          # Label name
              "color": "string",         # Label color (hex)
              "description": "string"    # Label description
            }
          ],
          "milestone": {                 # Associated milestone (if any)
            "id": int,
            "number": int,
            "title": "string",
            "description": "string",
            "state": "string",           # "open" or "closed"
            "due_on": "string",         # Due date (ISO 8601)
            "html_url": "string"
          },
          "comments": int,               # Number of comments
          "comments_data": [             # Detailed comment data (if available)
            {
              "id": int,                 # Comment ID
              "user": {
                "login": "string",
                "id": int,
                "avatar_url": "string",
                "html_url": "string"
              },
              "body": "string",         # Comment content
              "created_at": "string",   # Comment creation time
              "updated_at": "string",   # Comment update time
              "html_url": "string"      # Comment URL
            }
          ],
          "reactions": {                 # Reaction counts
            "+1": int,
            "-1": int,
            "laugh": int,
            "hooray": int,
            "confused": int,
            "heart": int,
            "rocket": int,
            "eyes": int
          },
          "pull_request": {              # Pull request information (if applicable)
            "url": "string",
            "html_url": "string",
            "diff_url": "string",
            "patch_url": "string",
            "merged_at": "string",      # Merge timestamp (if merged)
            "merged": boolean,           # Whether PR was merged
            "mergeable": boolean,       # Whether PR can be merged
            "mergeable_state": "string", # Merge status
            "additions": int,           # Lines added
            "deletions": int,           # Lines deleted
            "changed_files": int        # Files changed
          },
          "locked": boolean,             # Whether issue is locked
          "active_lock_reason": "string", # Lock reason (if locked)
          "author_association": "string", # User's association with repo
          "draft": boolean,             # Whether PR is draft (if applicable)
          "body_html": "string",        # HTML rendered body
          "body_text": "string"         # Plain text body
        }
      }
      or an error dictionary with status and message.

  Repository examples:
  - Microsoft VSCode: owner="microsoft", repo="vscode"
  - Google Chromium: owner="google", repo="chromium"
  - Apache Kafka: owner="apache", repo="kafka"
  - Personal repository: owner="your-username", repo="your-project"

  Issue number examples:
  - Bug report: 12345
  - Feature request: 67890
  - Pull request: 54321 (GitHub uses same numbering for issues and PRs)

  Successful response example:
  {
    "status": "success",
    "issue": {
      "number": 12345,
      "title": "Fix memory leak in component X",
      "body": "Detailed description of the memory leak issue...",
      "state": "open",
      "created_at": "2023-01-15T10:30:00Z",
      "updated_at": "2023-01-20T14:25:00Z",
      "closed_at": null,
      "html_url": "https://github.com/org/repo/issues/12345",
      "user": {
        "login": "developer123",
        "id": 123456,
        "avatar_url": "https://avatars.githubusercontent.com/u/123456",
        "html_url": "https://github.com/developer123"
      },
      "assignees": [
        {
          "login": "maintainer1",
          "id": 654321,
          "avatar_url": "https://avatars.githubusercontent.com/u/654321",
          "html_url": "https://github.com/maintainer1"
        }
      ],
      "labels": [
        {
          "id": 123,
          "name": "bug",
          "color": "d73a4a",
          "description": "Something isn't working"
        },
        {
          "id": 456,
          "name": "high priority",
          "color": "b60205",
          "description": "High priority issue"
        }
      ],
      "milestone": {
        "id": 789,
        "number": 1,
        "title": "Release 2.0",
        "description": "Major release with new features",
        "state": "open",
        "due_on": "2023-03-01T00:00:00Z",
        "html_url": "https://github.com/org/repo/milestone/1"
      },
      "comments": 5,
      "comments_data": [
        {
          "id": 111111,
          "user": {
            "login": "developer456",
            "id": 234567,
            "avatar_url": "https://avatars.githubusercontent.com/u/234567",
            "html_url": "https://github.com/developer456"
          },
          "body": "I can reproduce this issue...",
          "created_at": "2023-01-16T09:15:00Z",
          "updated_at": "2023-01-16T09:15:00Z",
          "html_url": "https://github.com/org/repo/issues/12345#issuecomment-111111"
        }
      ],
      "reactions": {
        "+1": 3,
        "-1": 0,
        "laugh": 1,
        "hooray": 2,
        "confused": 0,
        "heart": 1,
        "rocket": 0,
        "eyes": 5
      },
      "locked": false,
      "active_lock_reason": null,
      "author_association": "CONTRIBUTOR",
      "body_html": "<p>Detailed description of the memory leak issue...</p>",
      "body_text": "Detailed description of the memory leak issue..."
    }
  }

  Error response example:
  {
    "status": "error",
    "message": "Issue not found: Repository 'nonexistent/repo' or issue number '99999' does not exist"
  }

  Common error scenarios:
  - Issue or repository not found
  - Repository is private and access is denied
  - Invalid issue number (non-positive or non-existent)
  - Network connectivity issues to GitHub API
  - Authentication or permission errors
  - Rate limiting exceeded
  - Repository has been archived or deleted

  Raises:
      ValueError: If owner, repo, or issue_number parameters are empty or invalid
      GitHubConnectionError: If unable to connect to GitHub API
      AuthenticationError: If authentication fails or token is invalid
      PermissionError: If user lacks permissions to access the repository
      NetworkError: If network connectivity issues occur
      RateLimitError: If GitHub API rate limit is exceeded
      IssueNotFoundError: If the specified issue does not exist
      RepositoryNotFoundError: If the specified repository does not exist
  """
  return github.gh_get_issue_content(owner, repo, issue_number)
