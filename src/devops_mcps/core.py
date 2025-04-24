# /Users/huangjien/workspace/devops-mcps/src/devops_mcps/core.py
import logging
from . import github, jenkins  # Import the github module and jenkins
import logging.handlers  # Import handlers
import sys
import argparse
from typing import List, Optional, Dict, Any, Union

# Third-party imports
from dotenv import load_dotenv
from importlib.metadata import version, PackageNotFoundError

# MCP imports
from mcp.server.fastmcp import FastMCP

# --- Logging Setup (BEFORE importing github) ---

# Define logging parameters
LOG_FILENAME = "mcp_server.log"
MAX_LOG_SIZE_MB = 4
MAX_BYTES = MAX_LOG_SIZE_MB * 1024 * 1024
BACKUP_COUNT = 0  # Set to 0 to overwrite (delete the old log on rotation)
# --- CHANGE LOG LEVEL HERE ---
LOG_LEVEL = logging.DEBUG  # Set the log level to DEBUG

# --- UPDATE FORMATTER HERE ---
# Create formatter - Added %(lineno)d for line number
log_formatter = logging.Formatter(
  "%(asctime)s - %(name)s - %(levelname)s:%(lineno)d - %(message)s"
)

# --- Configure Root Logger ---
root_logger = logging.getLogger()
root_logger.setLevel(LOG_LEVEL)  # Set the desired global level
root_logger.handlers.clear()  # Clear any existing handlers (important if run multiple times)

# --- Rotating File Handler ---
# Consider using an absolute path if the script's working directory might change
# log_file_path = os.path.join('/var/log/mcp', LOG_FILENAME) # Example absolute path
log_file_path = LOG_FILENAME  # Use relative path for simplicity here

try:
  rotating_handler = logging.handlers.RotatingFileHandler(
    filename=log_file_path,
    maxBytes=MAX_BYTES,
    backupCount=BACKUP_COUNT,
    encoding="utf-8",
  )
  rotating_handler.setFormatter(log_formatter)  # Apply updated formatter
  root_logger.addHandler(rotating_handler)
  file_logging_enabled = True
except Exception as file_log_error:
  # Log error to stderr if file handler setup fails
  # Use basicConfig temporarily for this error message if root logger has no handlers yet
  # --- Use updated format string in fallback ---
  logging.basicConfig(level=LOG_LEVEL, format=log_formatter._fmt, stream=sys.stderr)
  logging.error(
    f"Failed to configure file logging to {log_file_path}: {file_log_error}"
  )
  file_logging_enabled = False


# --- Console (stderr) Handler ---
try:
  console_handler = logging.StreamHandler(sys.stderr)
  console_handler.setFormatter(log_formatter)  # Apply updated formatter
  root_logger.addHandler(console_handler)
  console_logging_enabled = True
except Exception as console_log_error:
  # Less likely to fail, but handle anyway
  # --- Use updated format string in fallback ---
  logging.basicConfig(level=LOG_LEVEL, format=log_formatter._fmt, stream=sys.stderr)
  logging.error(f"Failed to configure console logging: {console_log_error}")
  console_logging_enabled = False

# --- Final Logging Setup Confirmation ---
# Initialize logger for this module AFTER handlers are added
logger = logging.getLogger(__name__)

log_destinations = []
if file_logging_enabled:
  log_destinations.append(
    f"File ({log_file_path}, MaxSize: {MAX_LOG_SIZE_MB}MB, Backups: {BACKUP_COUNT})"
  )
if console_logging_enabled:
  log_destinations.append("Console (stderr)")

if log_destinations:
  # Use getLevelName to show 'DEBUG' instead of the numeric value
  logger.info(
    f"Logging configured (Level: {logging.getLevelName(LOG_LEVEL)}) -> {' & '.join(log_destinations)}"
  )
else:
  # Should not happen if basicConfig fallback works, but as a safeguard
  print("CRITICAL: Logging could not be configured.", file=sys.stderr)


# --- Environment and Local Imports (AFTER logging setup) ---

load_dotenv()  # Load .env file

# --- Get Package Version ---
try:
    # Replace 'devops-mcps' if your actual distributable package name is different
    # This name usually comes from your pyproject.toml `[project] name`
    # or setup.py `name=` argument.
    package_version = version("devops-mcps")
except PackageNotFoundError:
    logger.warning(
        "Could not determine package version using importlib.metadata. "
        "Is the package installed correctly? Falling back to 'unknown'."
    )
    package_version = "?.?.?" # Provide a fallback

# --- MCP Server Setup ---

mcp = FastMCP(
  f"DevOps MCP Server v{package_version} (Github & Jenkins)",
  host="0.0.0.0",
  port=8000,
  settings={"initialization_timeout": 10, "request_timeout": 300},
)

# --- MCP Tools (Wrappers around github.py functions) ---
# (No changes needed in the tool definitions themselves)
# Debug logs added previously will now be shown due to LOG_LEVEL change


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
  logger.debug(
    f"Executing search_repositories with query: {query}"
  )  # This will now be logged
  return github.gh_search_repositories(query=query)


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
  logger.debug(
    f"Executing get_file_contents for {owner}/{repo}/{path}"
  )  # This will now be logged
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
  logger.debug(
    f"Executing list_commits for {owner}/{repo}, branch: {branch}"
  )  # This will now be logged
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
  logger.debug(
    f"Executing list_issues for {owner}/{repo}, state: {state}"
  )  # This will now be logged
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
  logger.debug(
    f"Executing get_repository for {owner}/{repo}"
  )  # This will now be logged
  return github.gh_get_repository(owner=owner, repo=repo)


@mcp.tool()
async def search_code(
  q: str,
  sort: str = "indexed",
  order: str = "desc",
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Search for code across GitHub repositories. Returns raw data for the first page.

  Args:
      q: Search query using GitHub code search syntax.
      sort: Sort field ('indexed' or 'best match'). Default: 'indexed'.
      order: Sort order ('asc' or 'desc'). Default: 'desc'.

  Returns:
      List of code result dictionaries (first page) or an error dictionary.
  """
  logger.debug(f"Executing search_code with query: {q}")  # This will now be logged
  return github.gh_search_code(q=q, sort=sort, order=order)


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
      build_number: Build number.

  Returns:
      The last 10KB of the build log (str) or an error dictionary.
  """
  logger.debug(
    f"Executing get_jenkins_build_log for job: {job_name}, build: {build_number}"
  )
  return jenkins.jenkins_get_build_log(job_name=job_name, build_number=build_number)


@mcp.tool()
async def get_all_jenkins_views() -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Get all views in jenkins.

  Returns:
      List of views or an error dictionary.
  """
  logger.debug("Executing get_all_jenkins_views")
  return jenkins.jenkins_get_all_views()


# --- Add the new MCP tool for build parameters ---
@mcp.tool()
async def get_jenkins_build_parameters(
  job_name: str, build_number: int
) -> Union[Dict[str, Any], Dict[str, str]]:
  """Get the parameters used for a specific Jenkins build.

  Args:
      job_name: Name of the Jenkins job.
      build_number: Build number.

  Returns:
      A dictionary containing the build parameters or an error dictionary.
  """
  logger.debug(
    f"Executing get_jenkins_build_parameters for job: {job_name}, build: {build_number}"
  )
  # Call the corresponding function in the jenkins module
  return jenkins.jenkins_get_build_parameters(
    job_name=job_name, build_number=build_number
  )


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
# (No changes needed in main() or main_sse())


def main():
  """Entry point for the CLI."""
  parser = argparse.ArgumentParser(
    description="DevOps MCP Server (PyGithub - Raw Output)"
  )
  parser.add_argument(
    "--transport",
    choices=["stdio", "sse"],
    default="stdio",
    help="Transport type (stdio or sse)",
  )

  args = parser.parse_args()

  # Check if the GitHub client initialized successfully (accessing the global 'g' from the imported module)
  if github.g is None:
    # Initialization logs errors/warnings, but we might want to prevent startup
    if github.GITHUB_TOKEN:
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
  mcp.run(transport=args.transport)


def main_sse():
  """Run the MCP server with SSE transport."""
  if "--transport" not in sys.argv:
    sys.argv.extend(["--transport", "sse"])
  elif "sse" not in sys.argv:
    try:
      idx = sys.argv.index("--transport")
      if idx + 1 < len(sys.argv):
        sys.argv[idx + 1] = "sse"
      else:
        sys.argv.append("sse")
    except ValueError:
      sys.argv.extend(["--transport", "sse"])

  main()


if __name__ == "__main__":
  main()
