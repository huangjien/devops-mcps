# /Users/huangjien/workspace/devops-mcps/src/devops_mcps/jenkins.py
import logging
import os
import re
from typing import List, Optional, Dict, Any, Union

# Third-party imports
from jenkinsapi.jenkins import Jenkins, JenkinsAPIException
from jenkinsapi.job import Job
from jenkinsapi.view import View
from requests.exceptions import ConnectionError

# --- Import field_validator instead of validator ---
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# --- Pydantic Models (Input Validation) ---


class GetJobsInput(BaseModel):
  pass  # No input parameters


class GetBuildLogInput(BaseModel):
  job_name: str
  build_number: int


class GetJobsUnderViewInput(BaseModel):
  view_name: str


class GetJobsByNameInput(BaseModel):
  job_name_pattern: str


# --- Jenkins Client Initialization ---

JENKINS_URL = os.environ.get("JENKINS_URL")
JENKINS_USER = os.environ.get("JENKINS_USER")
JENKINS_TOKEN = os.environ.get("JENKINS_TOKEN")
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
  if not j:
    logger.error("jenkins_get_jobs: Jenkins client not initialized.")
    return {"error": "Jenkins client not initialized."}
  try:
    jobs = j.get_jobs()
    logger.debug(f"Found {len(jobs)} jobs.")
    return [_to_dict(job) for job in jobs.values()]  # modified to use .values()
  except JenkinsAPIException as e:
    logger.error(f"jenkins_get_jobs Jenkins Error: {e}", exc_info=True)
    return {"error": f"Jenkins API Error: {e}"}
  except Exception as e:
    logger.error(f"Unexpected error in jenkins_get_jobs: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"}


def jenkins_get_build_log(
  job_name: str, build_number: int
) -> Union[str, Dict[str, str]]:
  """Internal logic for getting a build log (last 5KB)."""
  logger.debug(
    f"jenkins_get_build_log called for job: {job_name}, build: {build_number}"
  )
  if not j:
    logger.error("jenkins_get_build_log: Jenkins client not initialized.")
    return {"error": "Jenkins client not initialized."}
  try:
    input_data = GetBuildLogInput(job_name=job_name, build_number=build_number)
    job = j.get_job(input_data.job_name)
    build = job.get_build(input_data.build_number)
    if not build:
      return {
        "error": f"Build #{input_data.build_number} not found for job {input_data.job_name}"
      }
    log = build.get_console()
    return log[-5000:]  # Return only the last 5KB
  except JenkinsAPIException as e:
    logger.error(f"jenkins_get_build_log Jenkins Error: {e}", exc_info=True)
    return {"error": f"Jenkins API Error: {e}"}
  except Exception as e:
    logger.error(f"Unexpected error in jenkins_get_build_log: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"}


def jenkins_get_jobs_under_view(
  view_name: str,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Internal logic for getting jobs under a specific view."""
  logger.debug(f"jenkins_get_jobs_under_view called for view: {view_name}")
  if not j:
    logger.error("jenkins_get_jobs_under_view: Jenkins client not initialized.")
    return {"error": "Jenkins client not initialized."}
  try:
    input_data = GetJobsUnderViewInput(view_name=view_name)
    view = j.get_view(input_data.view_name)
    jobs = view.get_job_dict()
    logger.debug(f"Found {len(jobs)} jobs under view '{view_name}'.")
    return [_to_dict(j.get_job(job_name)) for job_name in jobs]
  except JenkinsAPIException as e:
    logger.error(f"jenkins_get_jobs_under_view Jenkins Error: {e}", exc_info=True)
    return {"error": f"Jenkins API Error: {e}"}
  except Exception as e:
    logger.error(f"Unexpected error in jenkins_get_jobs_under_view: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"}


def jenkins_get_jobs_by_name(
  job_name_pattern: str,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Internal logic for getting jobs that match a regex pattern."""
  logger.debug(f"jenkins_get_jobs_by_name called with pattern: {job_name_pattern}")
  if not j:
    logger.error("jenkins_get_jobs_by_name: Jenkins client not initialized.")
    return {"error": "Jenkins client not initialized."}
  try:
    input_data = GetJobsByNameInput(job_name_pattern=job_name_pattern)
    all_jobs = j.get_jobs()
    compiled_pattern = re.compile(input_data.job_name_pattern)
    matching_jobs = [
      all_jobs[job_name]
      for job_name in all_jobs
      if compiled_pattern.fullmatch(job_name)
    ]
    logger.debug(
      f"Found {len(matching_jobs)} jobs matching pattern '{job_name_pattern}'."
    )
    return [_to_dict(job) for job in matching_jobs]
  except JenkinsAPIException as e:
    logger.error(f"jenkins_get_jobs_by_name Jenkins Error: {e}", exc_info=True)
    return {"error": f"Jenkins API Error: {e}"}
  except Exception as e:
    logger.error(f"Unexpected error in jenkins_get_jobs_by_name: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"}


# --- Other potentially important functions ---
def jenkins_get_all_views() -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Get all the views from the Jenkins."""
  logger.debug("jenkins_get_all_views called")
  if not j:
    logger.error("jenkins_get_all_views: Jenkins client not initialized.")
    return {"error": "Jenkins client not initialized."}
  try:
    views = j.get_views()
    logger.debug(f"Found {len(views)} views.")
    return [_to_dict(view) for view in views.values()]  # modified to use .values()
  except JenkinsAPIException as e:
    logger.error(f"jenkins_get_all_views Jenkins Error: {e}", exc_info=True)
    return {"error": f"Jenkins API Error: {e}"}
  except Exception as e:
    logger.error(f"Unexpected error in jenkins_get_all_views: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"}


def jenkins_get_queue() -> Union[List[Dict[str, Any]], Dict[str, str]]:
  """Get the Jenkins build queue information."""
  logger.debug("jenkins_get_queue called")
  if not j:
    logger.error("jenkins_get_queue: Jenkins client not initialized.")
    return {"error": "Jenkins client not initialized."}
  try:
    queue = j.get_queue()
    logger.debug(f"Found {len(queue)} queue items.")
    return [_to_dict(q) for q in queue]
  except JenkinsAPIException as e:
    logger.error(f"jenkins_get_queue Jenkins Error: {e}", exc_info=True)
    return {"error": f"Jenkins API Error: {e}"}
  except Exception as e:
    logger.error(f"Unexpected error in jenkins_get_queue: {e}", exc_info=True)
    return {"error": f"An unexpected error occurred: {e}"}
