# /Users/huangjien/workspace/devops-mcps/src/devops_mcps/jenkins.py
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any, Union
import requests
import hashlib # Import hashlib for generating cache keys

# Third-party imports
from jenkinsapi.jenkins import Jenkins, JenkinsAPIException
from jenkinsapi.job import Job
from jenkinsapi.view import View
from jenkinsapi.build import Build
from requests.exceptions import ConnectionError

# --- Import the cache instance ---
from .cache import cache # Import the global cache instance

logger = logging.getLogger(__name__)

# --- Jenkins Client Initialization ---
# Removed module-level environment variable reads
j: Optional[Jenkins] = None


def initialize_jenkins_client():
  """Initializes the global Jenkins client 'j'."""
  global j
  if j:  # Already initialized
    return j

  # Read environment variables dynamically here
  JENKINS_URL = os.environ.get("JENKINS_URL")
  JENKINS_USER = os.environ.get("JENKINS_USER")
  JENKINS_TOKEN = os.environ.get("JENKINS_TOKEN")
  try:
      LOG_LENGTH = int(os.environ.get("LOG_LENGTH", 10240)) # Default to 10KB if not set or invalid
  except ValueError:
      logger.warning(f"Invalid LOG_LENGTH environment variable. Using default 10240.")
      LOG_LENGTH = 10240

  if JENKINS_URL and JENKINS_USER and JENKINS_TOKEN:
    try:
      # Consider adding a timeout to the Jenkins client initialization
      j = Jenkins(JENKINS_URL, username=JENKINS_USER, password=JENKINS_TOKEN, timeout=30)
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
    except Exception as e: # Catch potential timeout errors during init too
      logger.error(f"Unexpected error initializing authenticated Jenkins client: {e}")
      j = None
  else:
    logger.warning(
      "JENKINS_URL, JENKINS_USER, or JENKINS_TOKEN environment variable not set."
    )
    logger.warning("Jenkins related tools will have limited functionality.")
    j = None
  return j


# Do not call initialization at module load time


def _to_dict(obj: Any) -> Any:
  """Converts common Jenkins objects to dictionaries. Handles basic types and lists."""
  if isinstance(obj, (str, int, float, bool, type(None))):
    return obj
  if isinstance(obj, list):
    return [_to_dict(item) for item in obj]
  if isinstance(obj, dict):
    return {k: _to_dict(v) for k, v in obj.items()}

  # Use more robust attribute access if possible
  if isinstance(obj, Job):
      data = {
          "name": getattr(obj, 'name', None),
          "url": getattr(obj, 'baseurl', None),
      }
      try:
          data["is_enabled"] = obj.is_enabled()
      except Exception: data["is_enabled"] = None
      try:
          data["is_queued"] = obj.is_queued()
          data["in_queue"] = data["is_queued"]
      except Exception:
          data["is_queued"] = None
          data["in_queue"] = None
      try:
          data["last_build_number"] = obj.get_last_buildnumber()
      except Exception: data["last_build_number"] = None

      # --- Start Modification ---
      try:
          # Get the last build object first
          last_build = obj.get_last_build()
          # Access the url attribute if the build exists
          data["last_build_url"] = last_build.url if last_build else None
      except Exception:
          data["last_build_url"] = None
      # --- End Modification ---
      return data

  if isinstance(obj, View):
      data = {
          "name": getattr(obj, 'name', None),
          "url": getattr(obj, 'baseurl', None),
      }
      try:
          data["description"] = obj.get_description()
      except Exception: data["description"] = None
      return data

  # Fallback
  try:
    return str(obj)
  except Exception as fallback_err:  # Catch potential errors during fallback
    logger.error(
      f"Error during fallback _to_dict for {type(obj).__name__}: {fallback_err}"
    )
    return f"<Error serializing object of type {type(obj).__name__}>"


# --- Jenkins API Functions (Internal Logic) ---
# These functions contain the core Jenkins interaction logic

# --- Manual Cache Integration ---
def jenkins_get_jobs() -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Internal logic for getting all jobs. Results are cached."""
  cache_key = "jenkins_jobs"
  ttl = 600 # Cache job list for 10 minutes

  # Check cache first
  cached_result = cache.get(cache_key)
  if cached_result is not None:
    logger.debug(f"Returning cached result for {cache_key}")
    return cached_result

  logger.debug(f"Executing jenkins_get_jobs (cache miss for {cache_key})")
  if not j:
    logger.error("jenkins_get_jobs: Jenkins client not initialized.")
    return {"error": "Jenkins client not initialized."} # Do not cache errors

  try:
    job_iterator = j.get_jobs()
    jobs_list = [_to_dict(job) for job in job_iterator]
    logger.debug(f"Found {len(jobs_list)} jobs.")
    # Cache the successful result
    cache.set(cache_key, jobs_list, ttl=ttl)
    return jobs_list
  except JenkinsAPIException as e:
    logger.error(f"jenkins_get_jobs Jenkins Error: {e}", exc_info=True)
    return {"error": f"Jenkins API Error: {e}"} # Do not cache errors
  except Exception as e:
    logger.error(f"Unexpected error in jenkins_get_jobs: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"} # Do not cache errors


# --- Manual Cache Integration ---
def jenkins_get_build_log(
  job_name: str, build_number: int
) -> Union[str, Dict[str, str]]:
  """Internal logic for getting a build log (last LOG_LENGTH bytes). Results are cached."""
  import os
  try:
      LOG_LENGTH = int(os.environ.get("LOG_LENGTH", 10240)) # Default to 10KB if not set or invalid
  except ValueError:
      logger.warning(f"Invalid LOG_LENGTH environment variable. Using default 10240.")
      LOG_LENGTH = 10240

  # Use a stable hash for the cache key
  key_hash = hashlib.sha256(f"{job_name}_{build_number}".encode()).hexdigest()
  cache_key = f"jenkins_log_{key_hash}"
  ttl = 3600 # Cache build logs for 1 hour

  # Check cache first
  cached_result = cache.get(cache_key)
  if cached_result is not None:
    logger.debug(f"Returning cached result for {cache_key} (job: {job_name}, build: {build_number})")
    return cached_result

  logger.debug(
    f"Executing jenkins_get_build_log (cache miss for {cache_key}) for job: {job_name}, build: {build_number}"
  )
  if not j:
    logger.error("jenkins_get_build_log: Jenkins client not initialized.")
    return {"error": "Jenkins client not initialized."} # Do not cache errors

  try:
    job = j.get_job(job_name)
    build = job.get_build(build_number)
    if not build:
      logger.warning(f"Build #{build_number} not found for job {job_name}")
      # Don't cache "not found" errors as they might appear later
      return {"error": f"Build #{build_number} not found for job {job_name}"}

    log = build.get_console()
    # Return only the last LOG_LENGTH bytes
    log_tail = log[-LOG_LENGTH:]
    logger.debug(f"Returning last {len(log_tail)} bytes of log for {job_name}#{build_number}")
    # Cache the successful result
    cache.set(cache_key, log_tail, ttl=ttl)
    return log_tail
  except JenkinsAPIException as e:
    logger.error(f"jenkins_get_build_log Jenkins Error: {e}", exc_info=True)
    return {"error": f"Jenkins API Error: {e}"} # Do not cache errors
  except Exception as e:
    logger.error(f"Unexpected error in jenkins_get_build_log: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"} # Do not cache errors


# --- Manual Cache Integration ---
def jenkins_get_all_views() -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Get all the views from the Jenkins. Results are cached."""
  cache_key = "jenkins_views"
  ttl = 600 # Cache view list for 10 minutes

  # Check cache first
  cached_result = cache.get(cache_key)
  if cached_result is not None:
    logger.debug(f"Returning cached result for {cache_key}")
    return cached_result

  logger.debug(f"Executing jenkins_get_all_views (cache miss for {cache_key})")
  if not j:
    logger.error("jenkins_get_all_views: Jenkins client not initialized.")
    return {"error": "Jenkins client not initialized."} # Do not cache errors

  try:
    views_list = [_to_dict(view) for _, view in j.views.items()] # Iterate through view objects
    logger.debug(f"Found {len(views_list)} views.")
    # Cache the successful result
    cache.set(cache_key, views_list, ttl=ttl)
    return views_list
  except JenkinsAPIException as e:
    logger.error(f"jenkins_get_all_views Jenkins Error: {e}", exc_info=True)
    return {"error": f"Jenkins API Error: {e}"} # Do not cache errors
  except Exception as e:
    logger.error(f"Unexpected error in jenkins_get_all_views: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"} # Do not cache errors


# --- Manual Cache Integration ---
def jenkins_get_recent_failed_builds(
  hours_ago: int = 8,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """
  Internal logic for getting jobs whose LAST build failed within the specified recent period.
  Uses a single optimized API call for performance. Results are cached for a short duration.

  Args:
      hours_ago: How many hours back to check for failed builds.

  Returns:
      A list of dictionaries for jobs whose last build failed recently, or an error dictionary.
  """
  import os
  JENKINS_URL = os.environ.get("JENKINS_URL")
  JENKINS_USER = os.environ.get("JENKINS_USER")
  JENKINS_TOKEN = os.environ.get("JENKINS_TOKEN")
  cache_key = f"jenkins_recent_failed_{hours_ago}h"
  ttl = 300 # Cache recent failed builds for 5 minutes

  # Check cache first
  cached_result = cache.get(cache_key)
  if cached_result is not None:
    logger.debug(f"Returning cached result for {cache_key}")
    return cached_result

  logger.debug(
    f"Executing jenkins_get_recent_failed_builds (cache miss for {cache_key}) for last {hours_ago} hours"
  )

  # Need credentials even if not using the 'j' client object directly for API calls
  if not JENKINS_URL or not JENKINS_USER or not JENKINS_TOKEN:
    logger.error("Jenkins credentials (URL, USER, TOKEN) not configured.")
    return {"error": "Jenkins credentials not configured."} # Do not cache errors

  recent_failed_builds = []
  try:
    # Calculate the cutoff time in UTC
    now_utc = datetime.now(timezone.utc)
    cutoff_utc = now_utc - timedelta(hours=hours_ago)
    logger.debug(f"Checking for LAST builds failed since {cutoff_utc.isoformat()}")

    # --- Optimized API Call ---
    api_url = f"{JENKINS_URL.rstrip('/')}/api/json?tree=jobs[name,url,lastBuild[number,timestamp,result,url]]"
    logger.debug(f"Making optimized API call to: {api_url}")
    response = requests.get(
      api_url,
      auth=(JENKINS_USER, JENKINS_TOKEN),
      timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    # --- End Optimized API Call ---

    if "jobs" not in data:
      logger.warning("No 'jobs' key found in Jenkins API response.")
      # Cache the empty list result
      cache.set(cache_key, [], ttl=ttl)
      return []

    # Process all builds across all jobs
    for job_data in data.get("jobs", []):
      job_name = job_data.get("name")
      builds = job_data.get("builds", [])
      
      if not job_name or not builds:
        continue
      
      for build in builds:
        build_timestamp_ms = build.get("timestamp")
        status = build.get("result")
        
        if not build_timestamp_ms or not status:
          continue
          
        build_timestamp_utc = datetime.fromtimestamp(
          build_timestamp_ms / 1000.0, tz=timezone.utc
        )
        
        if build_timestamp_utc >= cutoff_utc and status == "FAILURE":
          recent_failed_builds.append({
            "job_name": job_name,
            "build_number": build.get("number"),
            "status": status,
            "timestamp_utc": build_timestamp_utc.isoformat(),
            "url": build.get("url") or f"{job_data.get('url', '')}{build.get('number')}",
          })
          logger.info(f"Found failed build: {job_name}#{build.get('number')}")

    logger.debug(
      f"Finished processing optimized response. Found {len(recent_failed_builds)} jobs whose last build failed in the last {hours_ago} hours."
    )
    # Cache the successful result (even if it's an empty list)
    cache.set(cache_key, recent_failed_builds, ttl=ttl)
    return recent_failed_builds

  except requests.exceptions.Timeout as e:
    logger.error(f"Timeout error during optimized Jenkins API call: {e}", exc_info=True)
    return {"error": f"Timeout connecting to Jenkins API: {e}"} # Do not cache errors
  except requests.exceptions.ConnectionError as e:
    logger.error(
      f"Connection error during optimized Jenkins API call: {e}", exc_info=True
    )
    return {"error": f"Could not connect to Jenkins API: {e}"} # Do not cache errors
  except requests.exceptions.HTTPError as e:
    logger.error(
      f"HTTP error during optimized Jenkins API call: {e.response.status_code} - {e.response.text}",
      exc_info=True,
    )
    return {
      "error": f"Jenkins API HTTP Error: {e.response.status_code} - {e.response.reason}"
    } # Do not cache errors
  except requests.exceptions.RequestException as e:
    logger.error(f"Error during optimized Jenkins API call: {e}", exc_info=True)
    return {"error": f"Jenkins API Request Error: {e}"} # Do not cache errors
  except Exception as e:
    logger.error(
      f"Unexpected error in jenkins_get_recent_failed_builds (optimized): {e}",
      exc_info=True,
    )
    return {"error": f"An unexpected error occurred: {e}"} # Do not cache errors

