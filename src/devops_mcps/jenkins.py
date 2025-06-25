# /Users/huangjien/workspace/devops-mcps/src/devops_mcps/jenkins.py
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any, Union
import requests

# Third-party imports
from jenkinsapi.jenkins import Jenkins, JenkinsAPIException
from jenkinsapi.job import Job
from jenkinsapi.view import View
from jenkinsapi.build import Build
from requests.exceptions import ConnectionError

# Internal imports
from .cache import cache

logger = logging.getLogger(__name__)

# --- Jenkins Client Initialization ---
JENKINS_URL = os.environ.get("JENKINS_URL")
JENKINS_USER = os.environ.get("JENKINS_USER")
JENKINS_TOKEN = os.environ.get("JENKINS_TOKEN")
LOG_LENGTH = os.environ.get("LOG_LENGTH", 10240)  # Default to 10KB if not set
j: Optional[Jenkins] = None


def initialize_jenkins_client():
  """Initializes the global Jenkins client 'j'."""
  global j
  if j:  # Already initialized
    return j

  if JENKINS_URL and JENKINS_USER and JENKINS_TOKEN:
    try:
      j = Jenkins(JENKINS_URL, username=JENKINS_USER, password=JENKINS_TOKEN)
      # Basic connection test
      _ = j.get_master_data()
      logger.info(
        "Successfully authenticated with Jenkins using JENKINS_URL, JENKINS_USER and JENKINS_TOKEN."
      )
    except JenkinsAPIException as e:
      logger.error(f"Failed to initialize authenticated Jenkins client: {e}")
      j = None
    except ConnectionError as e:
      logger.error(f"Failed to connect to Jenkins server: {e}")
      j = None
    except Exception as e:
      logger.error(f"Unexpected error initializing authenticated Jenkins client: {e}")
      j = None
  else:
    logger.warning(
      "JENKINS_URL, JENKINS_USER, or JENKINS_TOKEN environment variable not set."
    )
    logger.warning("Jenkins related tools will have limited functionality.")
    j = None
  return j


# Call initialization when the module is loaded
if not any("pytest" in arg or "unittest" in arg for arg in sys.argv):
  initialize_jenkins_client()


# --- Helper Functions for Object Conversion (to Dict) ---


def _to_dict(obj: Any) -> Any:
  """Converts common Jenkins objects to dictionaries. Handles basic types and lists."""
  if isinstance(obj, (str, int, float, bool, type(None))):
    return obj
  if isinstance(obj, list):
    return [_to_dict(item) for item in obj]
  if isinstance(obj, dict):
    return {k: _to_dict(v) for k, v in obj.items()}

  if isinstance(obj, Job):
    return {
      "name": obj.name,
      "url": obj.baseurl,
      "is_enabled": obj.is_enabled(),
      "is_queued": obj.is_queued(),
      "in_queue": obj.is_queued(),  # corrected typo: in_queue
      "last_build_number": obj.get_last_buildnumber(),
      "last_build_url": obj.get_last_buildurl(),
    }
  if isinstance(obj, View):
    return {"name": obj.name, "url": obj.baseurl, "description": obj.get_description()}

  # Fallback
  try:
    logger.warning(
      f"No specific _to_dict handler for type {type(obj).__name__}, returning string representation."
    )
    return str(obj)
  except Exception as fallback_err:  # Catch potential errors during fallback
    logger.error(
      f"Error during fallback _to_dict for {type(obj).__name__}: {fallback_err}"
    )
    return f"<Error serializing object of type {type(obj).__name__}>"


# --- Jenkins API Functions (Internal Logic) ---
# These functions contain the core Jenkins interaction logic


def jenkins_get_jobs() -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Internal logic for getting all jobs."""
  logger.debug("jenkins_get_jobs called")

  # Check cache first
  cache_key = "jenkins:jobs:all"
  cached = cache.get(cache_key)
  if cached:
    logger.debug(f"Returning cached result for {cache_key}")
    return cached

  if not j:
    logger.error("jenkins_get_jobs: Jenkins client not initialized.")
    if not JENKINS_URL or not JENKINS_USER or not JENKINS_TOKEN:
      logger.error("Jenkins credentials not configured.")
      return {
        "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
      }
    return {
      "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
    }
  try:
    jobs = j.keys()
    logger.debug(f"Found {len(jobs)} jobs.")
    result = [_to_dict(job) for job in jobs]  # modified to use .values()
    cache.set(cache_key, result, ttl=300)  # Cache for 5 minutes
    return result
  except JenkinsAPIException as e:
    logger.error(f"jenkins_get_jobs Jenkins Error: {e}", exc_info=True)
    return {"error": f"Jenkins API Error: {e}"}
  except Exception as e:
    logger.error(f"Unexpected error in jenkins_get_jobs: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"}


def jenkins_get_build_log(
  job_name: str, build_number: int
) -> Union[str, Dict[str, str]]:
  """Internal logic for getting a build log (last 5KB).
  If build_number <= 0, returns the latest build log."""
  logger.debug(
    f"jenkins_get_build_log called for job: {job_name}, build: {build_number}"
  )

  if not j:
    logger.error("jenkins_get_build_log: Jenkins client not initialized.")
    if not JENKINS_URL or not JENKINS_USER or not JENKINS_TOKEN:
      logger.error("Jenkins credentials not configured.")
      return {
        "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
      }
    return {
      "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
    }

  try:
    job = j.get_job(job_name)
    if build_number <= 0:
      build_number = job.get_last_buildnumber()
      logger.debug(f"Using latest build number: {build_number}")

    # Check cache after we know the actual build number
    cache_key = f"jenkins:build_log:{job_name}:{build_number}"
    cached = cache.get(cache_key)
    if cached:
      logger.debug(f"Returning cached result for {cache_key}")
      return cached

    build = job.get_build(build_number)
    if not build:
      return {"error": f"Build #{build_number} not found for job {job_name}"}
    log = build.get_console()
    # Sanitize the log content to handle special characters
    if isinstance(log, str):
      # Replace or remove problematic control characters while preserving valid whitespace
      log = "".join(
        char if char.isprintable() or char in "\n\r\t" else " " for char in log
      )
      # Ensure proper UTF-8 encoding
      log = log.encode("utf-8", errors="replace").decode("utf-8")
    result = log[-LOG_LENGTH:]  # Return only the last portion
    cache.set(cache_key, result, ttl=1800)  # Cache for 30 minutes
    return result
  except JenkinsAPIException as e:
    logger.error(f"jenkins_get_build_log Jenkins Error: {e}", exc_info=True)
    return {"error": f"Jenkins API Error: {e}"}
  except Exception as e:
    logger.error(f"Unexpected error in jenkins_get_build_log: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"}


# --- Other potentially important functions ---
def jenkins_get_all_views() -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Get all the views from the Jenkins."""
  logger.debug("jenkins_get_all_views called")

  # Check cache first
  cache_key = "jenkins:views:all"
  cached = cache.get(cache_key)
  if cached:
    logger.debug(f"Returning cached result for {cache_key}")
    return cached

  if not j:
    logger.error("jenkins_get_all_views: Jenkins client not initialized.")
    if not JENKINS_URL or not JENKINS_USER or not JENKINS_TOKEN:
      logger.error("Jenkins credentials not configured.")
      return {
        "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
      }
    return {
      "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
    }
  try:
    views = j.views.keys()
    logger.debug(f"Found {len(views)} views.")
    result = [_to_dict(view) for view in views]  # modified to use .values()
    cache.set(cache_key, result, ttl=600)  # Cache for 10 minutes
    return result
  except JenkinsAPIException as e:
    logger.error(f"jenkins_get_all_views Jenkins Error: {e}", exc_info=True)
    return {"error": f"Jenkins API Error: {e}"}
  except Exception as e:
    logger.error(f"Unexpected error in jenkins_get_all_views: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"}


# --- Add new function to get build parameters ---
def jenkins_get_build_parameters(
  job_name: str, build_number: int
) -> Union[Dict[str, Any], Dict[str, str]]:
  """Internal logic for getting build parameters."""
  logger.debug(
    f"jenkins_get_build_parameters called for job: {job_name}, build: {build_number}"
  )

  # Check cache first
  cache_key = f"jenkins:build_parameters:{job_name}:{build_number}"
  cached = cache.get(cache_key)
  if cached:
    logger.debug(f"Returning cached result for {cache_key}")
    return cached

  if not j:
    logger.error("jenkins_get_build_parameters: Jenkins client not initialized.")
    if not JENKINS_URL or not JENKINS_USER or not JENKINS_TOKEN:
      logger.error("Jenkins credentials not configured.")
      return {
        "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
      }
    return {
      "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
    }
  try:
    job: Job = j.get_job(job_name)
    build: Optional[Build] = job.get_build(build_number)

    if not build:
      logger.warning(f"Build #{build_number} not found for job {job_name}")
      return {"error": f"Build #{build_number} not found for job {job_name}"}

    params: Dict[str, Any] = build.get_params()  # Get the parameters
    logger.debug(f"Retrieved parameters for build {job_name}#{build_number}: {params}")
    cache.set(cache_key, params, ttl=3600)  # Cache for 1 hour
    return params  # Return the dictionary directly

  except JenkinsAPIException as e:
    # Check for specific errors like job not found
    if "No such job" in str(e):  # Example check
      logger.warning(f"Job '{job_name}' not found.")
      return {"error": f"Job '{job_name}' not found."}
    logger.error(f"jenkins_get_build_parameters Jenkins Error: {e}", exc_info=True)
    return {
      "error": f"Jenkins API Error: {str(e)}"
    }  # Return string representation of error
  except Exception as e:
    logger.error(
      f"Unexpected error in jenkins_get_build_parameters: {e}", exc_info=True
    )
    return {"error": f"An unexpected error occurred: {e}"}


# --- Add the previously uncalled function (optional, but good practice if needed) ---
def jenkins_get_queue() -> Union[Dict[str, Any], Dict[str, str]]:
  """Get the current Jenkins queue information."""
  logger.debug("jenkins_get_queue called")

  # Check cache first
  cache_key = "jenkins:queue:current"
  cached = cache.get(cache_key)
  if cached:
    logger.debug(f"Returning cached result for {cache_key}")
    return cached

  if not j:
    logger.error("jenkins_get_queue: Jenkins client not initialized.")
    if not JENKINS_URL or not JENKINS_USER or not JENKINS_TOKEN:
      logger.error("Jenkins credentials not configured.")
      return {
        "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
      }
    return {
      "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
    }
  try:
    queue_info = j.get_queue().get_queue_items()  # Example: get items
    logger.debug(f"Retrieved queue info: {queue_info}")
    # Note: jenkinsapi might return specific objects here, adjust _to_dict or processing as needed
    result = {"queue_items": _to_dict(queue_info)}  # Wrap in a dict for clarity
    cache.set(
      cache_key, result, ttl=60
    )  # Cache for 1 minute (queue changes frequently)
    return result
  except JenkinsAPIException as e:
    logger.error(f"jenkins_get_queue Jenkins Error: {e}", exc_info=True)
    return {"error": f"Jenkins API Error: {str(e)}"}
  except Exception as e:
    logger.error(f"Unexpected error in jenkins_get_queue: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"}


# --- End jenkins_get_queue ---


def jenkins_get_recent_failed_builds(
  hours_ago: int = 8,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """
  Internal logic for getting jobs whose LAST build failed within the specified recent period.
  Uses a single optimized API call for performance.

  Args:
      hours_ago: How many hours back to check for failed builds.

  Returns:
      A list of dictionaries for jobs whose last build failed recently, or an error dictionary.
  """
  logger.debug(
    f"jenkins_get_recent_failed_builds (OPTIMIZED) called for the last {hours_ago} hours"
  )

  # Check cache first
  cache_key = f"jenkins:recent_failed_builds:{hours_ago}"
  cached = cache.get(cache_key)
  if cached:
    logger.debug(f"Returning cached result for {cache_key}")
    return cached

  # Need credentials even if not using the 'j' client object directly for API calls
  if not JENKINS_URL or not JENKINS_USER or not JENKINS_TOKEN:
    logger.error("Jenkins credentials (URL, USER, TOKEN) not configured.")
    return {
      "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
    }

  recent_failed_builds = []
  try:
    # Calculate the cutoff time in UTC
    now_utc = datetime.now(timezone.utc)
    cutoff_utc = now_utc - timedelta(hours=hours_ago)
    logger.debug(f"Checking for LAST builds failed since {cutoff_utc.isoformat()}")

    # --- Optimized API Call ---
    # Construct the API URL with the tree parameter
    # Request job name, url, and details of the lastBuild
    api_url = f"{JENKINS_URL.rstrip('/')}/api/json?tree=jobs[name,url,lastBuild[number,timestamp,result,url]]"
    logger.debug(f"Making optimized API call to: {api_url}")

    # Make the authenticated request (adjust timeout as needed)
    response = requests.get(
      api_url,
      auth=(JENKINS_USER, JENKINS_TOKEN),
      timeout=60,  # Set a reasonable timeout for this single large request (e.g., 60 seconds)
    )
    response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

    data = response.json()
    # --- End Optimized API Call ---

    if "jobs" not in data:
      logger.warning("No 'jobs' key found in Jenkins API response.")
      return []  # Return empty list if no jobs data

    # Iterate through the jobs data obtained from the single API call
    for job_data in data.get("jobs", []):
      job_name = job_data.get("name")
      last_build_data = job_data.get("lastBuild")

      if not job_name:
        logger.warning("Found job data with no name, skipping.")
        continue

      logger.debug(f"Processing job: {job_name} from optimized response")

      if not last_build_data:
        logger.debug(
          f"  Job '{job_name}' has no lastBuild information in the response."
        )
        continue

      # Extract last build details
      build_number = last_build_data.get("number")
      build_timestamp_ms = last_build_data.get("timestamp")
      status = last_build_data.get(
        "result"
      )  # 'result' usually holds FAILURE, SUCCESS, etc.
      build_url = last_build_data.get("url")

      if not build_timestamp_ms:
        logger.warning(
          f"Last build for {job_name} (Num: {build_number}) missing timestamp data. Skipping."
        )
        continue

      # Convert timestamp and check time window
      build_timestamp_utc = datetime.fromtimestamp(
        build_timestamp_ms / 1000.0, tz=timezone.utc
      )

      if build_timestamp_utc >= cutoff_utc:
        logger.debug(
          f"  Last build {job_name}#{build_number} is recent ({build_timestamp_utc.isoformat()}). Status: {status}"
        )
        # Check status
        if status == "FAILURE":
          recent_failed_builds.append(
            {
              "job_name": job_name,
              "build_number": build_number,
              "status": status,
              "timestamp_utc": build_timestamp_utc.isoformat(),
              "url": build_url
              or job_data.get("url", "") + str(build_number),  # Construct URL if needed
            }
          )
          logger.info(f"Found recent failed LAST build: {job_name}#{build_number}")
        else:
          logger.debug(
            f"  Last build {job_name}#{build_number} was recent but status was not FAILURE (Status: {status})."
          )
      else:
        logger.debug(
          f"  Last build {job_name}#{build_number} ({build_timestamp_utc.isoformat()}) is older than cutoff ({cutoff_utc.isoformat()}). Skipping."
        )

    logger.debug(
      f"Finished processing optimized response. Found {len(recent_failed_builds)} jobs whose last build failed in the last {hours_ago} hours."
    )
    cache.set(cache_key, recent_failed_builds, ttl=300)  # Cache for 5 minutes
    return recent_failed_builds

  except requests.exceptions.Timeout as e:
    logger.error(f"Timeout error during optimized Jenkins API call: {e}", exc_info=True)
    return {"error": f"Timeout connecting to Jenkins API: {e}"}
  except requests.exceptions.ConnectionError as e:
    logger.error(
      f"Connection error during optimized Jenkins API call: {e}", exc_info=True
    )
    return {"error": f"Could not connect to Jenkins API: {e}"}
  except requests.exceptions.HTTPError as e:
    logger.error(
      f"HTTP error during optimized Jenkins API call: {e.response.status_code} - {e.response.text}",
      exc_info=True,
    )
    return {
      "error": f"Jenkins API HTTP Error: {e.response.status_code} - {e.response.reason}"
    }
  except requests.exceptions.RequestException as e:
    logger.error(f"Error during optimized Jenkins API call: {e}", exc_info=True)
    return {"error": f"Jenkins API Request Error: {e}"}
  except Exception as e:  # Catch other potential errors (e.g., JSON parsing)
    logger.error(
      f"Unexpected error in jenkins_get_recent_failed_builds (optimized): {e}",
      exc_info=True,
    )
    return {"error": f"An unexpected error occurred: {e}"}


def set_jenkins_client_for_testing(client):
  global j
  j = client
