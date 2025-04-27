import unittest
import logging
from io import StringIO
from unittest.mock import MagicMock, patch
import os
from devops_mcps.jenkins_sample import (
  get_failed_jobs,
  diagnose_failure,
  jenkins_failure_diagnosis_prompt,
  get_jenkins_diagnosis_prompt,
)

# Setup logging for tests
logging.basicConfig(level=logging.DEBUG)

# Mock environment variables at module level
os.environ["JENKINS_URL"] = "http://fake-jenkins.com"
os.environ["JENKINS_USER"] = "testuser"
os.environ["JENKINS_TOKEN"] = "testtoken"


class TestJenkinsSample(unittest.TestCase):
  def test_jenkins_failure_diagnosis_prompt(self):
    # Test with error patterns
    log = "Build timeout occurred"
    result = jenkins_failure_diagnosis_prompt("test_job", log)
    self.assertIn("Build timeout", result["suggestions"][0])
    self.assertEqual(len(result["steps"]), 2)

    # Test without error patterns
    log = "Build successful"
    result = jenkins_failure_diagnosis_prompt("test_job", log)
    self.assertIn("No specific patterns detected", result["suggestions"][0])

  def setUp(self):
    # Mock Jenkins API
    self.mock_job_instance = MagicMock()
    self.mock_build = MagicMock()
    self.mock_jenkins = MagicMock()
    self.mock_jenkins.baseurl = "http://fake-jenkins.com"
    self.mock_jenkins.get_jobs.return_value = {
      "job1": self.mock_job_instance,
      "job2": self.mock_job_instance,
    }
    # Patch the global jenkins instance
    self.patcher = patch("devops_mcps.jenkins_sample.jenkins", new=self.mock_jenkins)
    self.patcher.start()
    self.addCleanup(self.patcher.stop)
    self.mock_job_instance.get_last_build.return_value = self.mock_build
    self.mock_build.get_status.return_value = "FAILURE"
    self.mock_build.get_console.return_value = "ERROR: Something went wrong"

    # Patch environment variables
    patcher = patch.dict(
      "os.environ",
      {
        "JENKINS_URL": "http://fake-jenkins.com",
        "JENKINS_USER": "user",
        "JENKINS_TOKEN": "token",
      },
    )
    self.addCleanup(patcher.stop)
    patcher.start()

    # Configure logger to capture logs
    self.logger = logging.getLogger("jenkins_sample")
    self.logger.setLevel(logging.DEBUG)
    self.log_capture = StringIO()
    self.handler = logging.StreamHandler(self.log_capture)
    self.handler.setLevel(logging.DEBUG)
    self.logger.addHandler(self.handler)
    self.addCleanup(self.handler.close)
    # Ensure logs are propagated
    self.logger.propagate = True
    # Patch the logger in the module
    self.logger_patcher = patch("devops_mcps.jenkins_sample.logger", new=self.logger)
    self.logger_patcher.start()
    self.addCleanup(self.logger_patcher.stop)

  def test_get_failed_jobs(self):
    # Simulate failed job
    self.mock_build.get_status.return_value = "FAILURE"
    self.mock_jenkins.get_jobs.return_value = {"job1": self.mock_job_instance}
    failed_jobs = get_failed_jobs()
    self.assertEqual(len(failed_jobs), 1)
    self.mock_jenkins.get_jobs.assert_called_once()
    self.assertIn("job1", failed_jobs)

  def test_diagnose_failure_with_error(self):
    # Simulate console output with error
    self.mock_build.get_console.return_value = "ERROR: Something went wrong"
    self.mock_jenkins.get_job.return_value = self.mock_job_instance
    logger = logging.getLogger("jenkins_sample")
    with self.assertLogs(logger, level="ERROR") as log:
      diagnose_failure("job1")
    self.mock_jenkins.get_job.assert_called_once_with("job1")
    self.assertIn(
      "ERROR:jenkins_sample:Error found in job job1: ERROR: Something went wrong",
      log.output,
    )

  def test_diagnose_failure_without_error(self):
    # Simulate console output without error
    self.mock_build.get_console.return_value = "All good"
    self.mock_jenkins.get_job.return_value = self.mock_job_instance
    logger = logging.getLogger("jenkins_sample")
    with self.assertLogs(logger, level="INFO") as log:
      diagnose_failure("job1")
    self.mock_jenkins.get_job.assert_called_once_with("job1")
    self.assertIn(
      "INFO:jenkins_sample:No specific error found in job job1.", log.output
    )

  def test_jenkins_failure_diagnosis_prompt_error_handling(self):
    # Test error handling in jenkins_failure_diagnosis_prompt
    with self.assertRaises(TypeError) as cm:
      jenkins_failure_diagnosis_prompt(None, None)
      self.assertEqual(str(cm.exception), "argument of type 'NoneType' is not iterable")
      jenkins_failure_diagnosis_prompt(None, None)
      self.assertEqual(str(cm.exception), "argument of type 'NoneType' is not iterable")

  def test_get_jenkins_diagnosis_prompt_error_handling(self):
    # Test error handling in get_jenkins_diagnosis_prompt
    with self.assertRaises(TypeError) as cm:
      jenkins_failure_diagnosis_prompt(None, None)
      self.assertEqual(str(cm.exception), "argument of type 'NoneType' is not iterable")
      get_jenkins_diagnosis_prompt(None, None)
    self.assertEqual(str(cm.exception), "argument of type 'NoneType' is not iterable")

  def test_jenkins_failure_diagnosis_prompt_log_analysis(self):
    # Test log analysis functionality
    log = "Compilation error: missing dependency"
    result = jenkins_failure_diagnosis_prompt("test_job", log)
    self.assertIn("Verify source code", result["steps"])
    self.assertIn("Check dependencies", result["steps"])

  def test_get_jenkins_diagnosis_prompt_log_analysis(self):
    # Test log analysis functionality
    with patch(
      "devops_mcps.jenkins_sample.jenkins_failure_diagnosis_prompt"
    ) as mock_diagnosis:
      mock_diagnosis.return_value = {
        "job_name": "test_job",
        "steps": ["Review test cases", "Check test environment"],
        "suggestions": ["Investigate Test failure issues"],
        "build_number": 123,
        "additional_resources": ["Jenkins documentation"],
      }
      result = get_jenkins_diagnosis_prompt("test_job", 123)
      self.assertEqual(result["job_name"], "test_job")
      self.assertEqual(result["build_number"], 123)
      self.assertIn("Review test cases", result["steps"])


if __name__ == "__main__":
  unittest.main()
