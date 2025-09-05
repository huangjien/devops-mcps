"""Jenkins build information retrieval functionality."""

import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Union, Any

# Internal imports
from .jenkins_helpers import (
  _get_jenkins_constants,
  _get_cache,
  check_jenkins_credentials,
)

logger = logging.getLogger(__name__)


def jenkins_get_recent_failed_builds(
  hours_ago: int = 24,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Get recent failed builds from Jenkins.

  Args:
      hours_ago: Number of hours to look back for failed builds

  Returns:
      List of failed build dictionaries or error dictionary
  """
  logger.debug(f"jenkins_get_recent_failed_builds called with hours_ago: {hours_ago}")

  # Check cache first
  cache_key = f"jenkins:recent_failed_builds:{hours_ago}"
  cache = _get_cache()
  cached_builds = cache.get(cache_key)
  if cached_builds:
    logger.debug(f"Returning cached recent failed builds for {cache_key}")
    return cached_builds

  # Check credentials
  credentials_error = check_jenkins_credentials()
  if credentials_error:
    return credentials_error

  constants = _get_jenkins_constants()

  try:
    # Calculate time threshold
    time_threshold = int(
      (datetime.now() - timedelta(hours=hours_ago)).timestamp() * 1000
    )

    # Get all jobs
    jobs_url = f"{constants['JENKINS_URL']}/api/json?tree=jobs[name,url,lastBuild[number,timestamp,result,url]]"
    response = requests.get(
      jobs_url,
      auth=(constants["JENKINS_USER"], constants["JENKINS_TOKEN"]),
      timeout=30,
    )
    response.raise_for_status()
    jobs_data = response.json()

    # Process jobs to find recent failed builds
    failed_builds = []
    for job in jobs_data.get("jobs", []):
      last_build = job.get("lastBuild")
      if not last_build:
        continue

      # Check if build is recent and failed
      timestamp = last_build.get("timestamp", 0)
      result = last_build.get("result")
      if timestamp > time_threshold and result == "FAILURE":
        build_info = {
          "job_name": job.get("name"),
          "build_number": last_build.get("number"),
          "timestamp": timestamp,
          "timestamp_iso": datetime.fromtimestamp(timestamp / 1000).isoformat(),
          "result": result,
        }

        # Add URLs if missing
        if "url" not in last_build and "url" in job:
          build_info["build_url"] = f"{job['url']}{last_build.get('number')}/"
        else:
          build_info["build_url"] = last_build.get("url")

        failed_builds.append(build_info)

    logger.debug(f"Found {len(failed_builds)} recent failed builds")
    cache.set(cache_key, failed_builds, ttl=300)  # Cache for 5 minutes
    return failed_builds

  except requests.exceptions.ConnectionError as e:
    logger.error(f"jenkins_get_recent_failed_builds connection error: {e}")
    return {"error": "Could not connect to Jenkins API"}
  except requests.exceptions.HTTPError as e:
    logger.error(f"jenkins_get_recent_failed_builds HTTP error: {e}")
    return {"error": f"Jenkins API HTTP Error: {e.response.status_code}"}
  except requests.exceptions.Timeout as e:
    logger.error(f"jenkins_get_recent_failed_builds timeout error: {e}")
    return {"error": "Timeout connecting to Jenkins API"}
  except requests.exceptions.RequestException as e:
    logger.error(f"jenkins_get_recent_failed_builds request error: {e}")
    return {"error": "Jenkins API Request Error"}
  except Exception as e:
    logger.error(f"jenkins_get_recent_failed_builds error: {e}")
    return {"error": f"An unexpected error occurred: {e}"}
