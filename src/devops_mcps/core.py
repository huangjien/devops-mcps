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
  f"DevOps MCP Server v{package_version} (Github & Jenkins)",
  host="0.0.0.0",
  port=8000,
  settings={"initialization_timeout": 10, "request_timeout": 300},
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
  """Get list of Azure subscriptions.

  Returns:
      List of subscription dictionaries or an error dictionary.
  """
  logger.debug("Executing get_azure_subscriptions")
  return azure.get_subscriptions()


@mcp.tool()
async def list_azure_vms(
  subscription_id: str,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """List all virtual machines in an Azure subscription.

  Args:
      subscription_id: Azure subscription ID.

  Returns:
      List of VM dictionaries or an error dictionary.
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
  """List all AKS clusters in an Azure subscription.

  Args:
      subscription_id: Azure subscription ID.

  Returns:
      List of AKS cluster dictionaries or an error dictionary.enve
  """
  logger.debug(f"Executing list_aks_clusters for subscription: {subscription_id}")
  if not subscription_id:
    logger.error("Parameter 'subscription_id' cannot be empty")
    return {"error": "Parameter 'subscription_id' cannot be empty"}
  return azure.list_aks_clusters(subscription_id)


@mcp.tool()
async def search_repositories(
  query: str,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Search for GitHub repositories. Returns raw data for the first page.

  Args:
      query: Search query using GitHub search syntax.

  Returns:
      List of repository dictionaries (first page) or an error dictionary.
  """
  logger.debug(f"Executing search_repositories with query: {query}")
  if not query:
    logger.error("Parameter 'query' cannot be empty")
    return {"error": "Parameter 'query' cannot be empty"}
  return github.gh_search_repositories(query=query)


@mcp.tool(
  name="github_get_current_user_info",
  description="Get the name and email of the currently authenticated GitHub user.",
)
async def github_get_current_user_info() -> dict:  # Removed g: Github parameter
  """
  Retrieves the name and email of the authenticated GitHub user.

  Returns:
      A dictionary containing the user's name and email, or an error message.
  """
  # Call the synchronous function from the github module directly
  # Note: This will block the event loop despite being in an async function.
  return (
    github.gh_get_current_user_info()
  )  # Removed try/except, error handling is in github.py


@mcp.tool()
async def get_file_contents(
  owner: str, repo: str, path: str, branch: Optional[str] = None
) -> Union[str, List[Dict[str, Any]], Dict[str, Any]]:
  """Get the contents of a file (decoded) or directory listing (list of dicts) from a GitHub repository.

  Args:
      owner: Repository owner (username or organization).
      repo: Repository name.
      path: Path to the file or directory.
      branch: Branch name (defaults to the repository's default branch).

  Returns:
      Decoded file content (str), list of file/dir dictionaries, or an error dictionary.
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
  owner: str, repo: str, branch: Optional[str] = None
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """List commits in a GitHub repository. Returns raw data for the first page.

  Args:
      owner: Repository owner (username or organization).
      repo: Repository name.
      branch: Branch name or SHA to list commits from (defaults to default branch).

  Returns:
      List of commit dictionaries (first page) or an error dictionary.
  """
  logger.debug(f"Executing list_commits for {owner}/{repo}, branch: {branch}")
  if not owner:
    logger.error("Parameter 'owner' cannot be empty")
    return {"error": "Parameter 'owner' cannot be empty"}
  if not repo:
    logger.error("Parameter 'repo' cannot be empty")
    return {"error": "Parameter 'repo' cannot be empty"}
  return github.gh_list_commits(owner=owner, repo=repo, branch=branch)


@mcp.tool()
async def list_issues(
  owner: str,
  repo: str,
  state: str = "open",
  labels: Optional[List[str]] = None,
  sort: str = "created",
  direction: str = "desc",
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """List issues in a GitHub repository. Returns raw data for the first page.

  Args:
      owner: Repository owner.
      repo: Repository name.
      state: Filter by state ('open', 'closed', 'all'). Default: 'open'.
      labels: Filter by labels (list of strings).
      sort: Sort by ('created', 'updated', 'comments'). Default: 'created'.
      direction: Sort direction ('asc', 'desc'). Default: 'desc'.

  Returns:
      List of issue dictionaries (first page) or an error dictionary.
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
  """Get information about a GitHub repository. Returns raw data.

  Args:
      owner: Repository owner (username or organization).
      repo: Repository name.

  Returns:
      Repository dictionary or an error dictionary.
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
  """Search for code in GitHub repositories. Returns raw data for the first page.

  Args:
      query: Search query using GitHub search syntax.

  Returns:
      List of code search result dictionaries (first page) or an error dictionary.
  """
  logger.debug(f"Executing search_code with query: {query}")
  if not query:
    logger.error("Parameter 'query' cannot be empty")
    return {"error": "Parameter 'query' cannot be empty"}
  return github.gh_search_code(query=query)


# --- MCP Jenkins Tools (Wrappers around jenkins.py functions) ---
@mcp.tool()
async def get_jenkins_jobs() -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Get all Jenkins jobs.

  Returns:
      List of job dictionaries or an error dictionary.
  """
  logger.debug("Executing get_jenkins_jobs")
  return jenkins.jenkins_get_jobs()


@mcp.tool()
async def get_jenkins_build_log(
  job_name: str, build_number: int
) -> Union[str, Dict[str, str]]:
  """Get the Jenkins build log for a specific job and build number (last 5KB).

  Args:
      job_name: Name of the Jenkins job.
      build_number: Build number, if 0 or minus, get the last build.

  Returns:
      The last 10KB of the build log (str) or an error dictionary.
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
  """Get all views in jenkins.

  Returns:
      List of views or an error dictionary.
  """
  logger.debug("Executing get_all_jenkins_views")
  return jenkins.jenkins_get_all_views()


@mcp.tool()
# --- ADD hours_ago parameter here ---
async def get_recent_failed_jenkins_builds(
  hours_ago: int = 8,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Get a list of Jenkins builds that failed within the specified recent period.

  Args: # Add Args section
      hours_ago (int, optional): How many hours back to check for failed builds. Defaults to 8.

  Returns:
      A list of dictionaries, each containing details ('job_name', 'build_number',
      'status', 'timestamp_utc', 'url') for builds that failed recently,
      or an error dictionary.
  """
  # --- Use the hours_ago variable in the log ---
  logger.debug(f"Executing get_recent_failed_jenkins_builds for last {hours_ago} hours")
  # --- Pass the hours_ago parameter ---
  return jenkins.jenkins_get_recent_failed_builds(hours_ago=hours_ago)


# --- End new MCP tool ---

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
    current_github_token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
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
      repository: The Artifactory repository name.
      path: The path within the repository (default: "/").

  Returns:
      List of item dictionaries or an error dictionary.
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
  """Search for items across multiple repositories in Artifactory.

  Args:
      query: The search query.
      repositories: Optional list of repositories to search in (if None, searches all).

  Returns:
      List of search result dictionaries or an error dictionary.
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
  """Get information about a specific item in Artifactory.

  Args:
      repository: The Artifactory repository name.
      path: The path to the item within the repository.

  Returns:
      Item information dictionary or an error dictionary.
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
  """Get GitHub issue content including comments, metadata, assignees, and creator.

  Args:
      owner: Repository owner username or organization.
      repo: Repository name.
      issue_number: GitHub issue number.

  Returns:
      dict: A dictionary containing issue details including title, body, labels,
          created_at, updated_at, comments, assignees, creator, and error status.
  """
  return github.gh_get_issue_content(owner, repo, issue_number)
