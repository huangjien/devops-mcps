import logging
from jenkinsapi.jenkins import Jenkins
from dotenv import load_dotenv
from unittest.mock import MagicMock
import os
from typing import List
# Setup logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Jenkins server URL and credentials from environment variables
# --- Jenkins Client Initialization ---
JENKINS_URL = os.environ.get("JENKINS_URL")
JENKINS_USER = os.environ.get("JENKINS_USER")
JENKINS_TOKEN = os.environ.get("JENKINS_TOKEN")

# Connect to Jenkins
if JENKINS_URL is not None and JENKINS_USER is not None and JENKINS_TOKEN is not None:
    try:
        jenkins = Jenkins(JENKINS_URL, username=JENKINS_USER, password=JENKINS_TOKEN)
    except Exception as e:
        logger.error(f"Failed to initialize Jenkins client: {e}")
        jenkins = MagicMock()
else:
    jenkins = MagicMock()
    jenkins.baseurl = 'http://fake-jenkins.com'


def get_failed_jobs() -> List[str]:
    """Retrieve recent failed Jenkins jobs."""
    try:
        failed_jobs = []
        jobs = jenkins.get_jobs()
        if not jobs:
            logger.warning("No jobs found in Jenkins")
            return []

        for job_name, job_instance in jobs.items():
            try:
                last_build = job_instance.get_last_build()
                if last_build.get_status() == 'FAILURE':
                    failed_jobs.append(job_name)
            except Exception as e:
                logger.error(f"Error processing job {job_name}: {e}")
        return failed_jobs
    except Exception as e:
        logger.error(f"Failed to get failed jobs: {e}")
        return []


def diagnose_failure(job_name: str) -> None:
    """Diagnose the root cause of a failed Jenkins job."""
    try:
        job_instance = jenkins.get_job(job_name)
        if not job_instance:
            logger.error(f"Job {job_name} not found")
            return

        last_build = job_instance.get_last_build()
        if not last_build:
            logger.error(f"No builds found for job {job_name}")
            return

        console_output = last_build.get_console()
        if not console_output:
            logger.warning(f"No console output for job {job_name}")
            return

        # Analyze console output for common error patterns
        if "ERROR" in console_output:
            logger.error(f"Error found in job {job_name}: {console_output}")
        else:
            logger.info(f"No specific error found in job {job_name}.")
    except Exception as e:
        logger.error(f"Failed to diagnose job {job_name}: {e}")


if __name__ == "__main__":
    failed_jobs = get_failed_jobs()
    for job in failed_jobs:
        diagnose_failure(job)