"""Extended tests for jenkins_job_api module."""

from unittest.mock import Mock, patch
import pytest

from devops_mcps.utils.jenkins.jenkins_job_api import (
  _extract_jobs_from_client,
  jenkins_get_jobs,
)


class TestExtractJobsFromClient:
  """Test cases for _extract_jobs_from_client function."""

  def test_extract_from_get_jobs_dict(self):
    """Test extraction when get_jobs() returns a dict."""
    mock_client = Mock()
    mock_client.get_jobs.return_value = {
      "job1": {"name": "job1"},
      "job2": {"name": "job2"},
    }

    result = _extract_jobs_from_client(mock_client)
    assert len(result) == 2
    assert {"name": "job1"} in result
    assert {"name": "job2"} in result

  def test_extract_from_get_jobs_list_of_tuples(self):
    """Test extraction when get_jobs() returns a list of tuples."""
    mock_client = Mock()
    mock_client.get_jobs.return_value = [
      ("job1", {"name": "job1"}),
      ("job2", {"name": "job2"}),
    ]

    result = _extract_jobs_from_client(mock_client)
    assert len(result) == 2
    assert {"name": "job1"} in result
    assert {"name": "job2"} in result

  def test_extract_from_get_jobs_simple_list(self):
    """Test extraction when get_jobs() returns a simple list."""
    mock_client = Mock()
    mock_client.get_jobs.return_value = [{"name": "job1"}, {"name": "job2"}]

    result = _extract_jobs_from_client(mock_client)
    assert len(result) == 2
    assert {"name": "job1"} in result

  def test_extract_from_get_jobs_values_method(self):
    """Test extraction when get_jobs() returns object with values() method."""
    mock_client = Mock()
    jobs_obj = Mock()
    jobs_obj.values.return_value = [{"name": "job1"}]
    # Ensure it's not treated as a list or dict first
    # The code checks isinstance(jobs_obj, dict) first, then list
    # We need it to fail those and fall through to hasattr(jobs_obj, "values")
    # Mock objects aren't dicts or lists by default, so this should work if we don't make it iterable in a way that looks like a list
    mock_client.get_jobs.return_value = jobs_obj

    result = _extract_jobs_from_client(mock_client)
    assert result == [{"name": "job1"}]

  def test_extract_from_get_jobs_iterable(self):
    """Test extraction when get_jobs() returns a generic iterable."""
    mock_client = Mock()
    # A list is an iterable, and the code converts generic iterables to list
    # jobs_list = list(jobs_obj)
    mock_client.get_jobs.return_value = [{"name": "job1"}]

    result = _extract_jobs_from_client(mock_client)
    assert result == [{"name": "job1"}]

  def test_extract_from_jobs_attribute_dict(self):
    """Test extraction when client has jobs attribute as dict."""
    mock_client = Mock()
    del mock_client.get_jobs  # Ensure get_jobs doesn't exist
    mock_client.jobs = {"job1": {"name": "job1"}}

    result = _extract_jobs_from_client(mock_client)
    assert len(result) == 1
    assert result[0] == {"name": "job1"}

  def test_extract_from_jobs_attribute_values(self):
    """Test extraction when client has jobs attribute with values()."""
    mock_client = Mock()
    del mock_client.get_jobs
    jobs_obj = Mock()
    jobs_obj.values.return_value = [{"name": "job1"}]
    mock_client.jobs = jobs_obj

    result = _extract_jobs_from_client(mock_client)
    assert result == [{"name": "job1"}]

  def test_extract_from_jobs_attribute_list_tuples(self):
    """Test extraction when client has jobs attribute as list of tuples."""
    mock_client = Mock()
    del mock_client.get_jobs
    mock_client.jobs = [("job1", {"name": "job1"})]

    result = _extract_jobs_from_client(mock_client)
    assert result == [{"name": "job1"}]

  def test_extract_from_client_values(self):
    """Test extraction when client itself has values() method."""
    mock_client = Mock()
    del mock_client.get_jobs
    del mock_client.jobs
    mock_client.values.return_value = [{"name": "job1"}]

    result = _extract_jobs_from_client(mock_client)
    assert result == [{"name": "job1"}]

  def test_extract_failure(self):
    """Test failure when no suitable method found."""
    mock_client = Mock()
    del mock_client.get_jobs
    del mock_client.jobs
    del mock_client.values

    with pytest.raises(
      AttributeError, match="Jenkins client does not expose jobs list"
    ):
      _extract_jobs_from_client(mock_client)


class TestJenkinsGetJobsExtended:
  """Extended test cases for jenkins_get_jobs function."""

  @patch("devops_mcps.utils.jenkins.jenkins_job_api._get_cache")
  @patch("devops_mcps.utils.jenkins.jenkins_job_api.requests.get")
  @patch("devops_mcps.utils.jenkins.jenkins_job_api._get_jenkins_constants")
  def test_jenkins_get_jobs_empty_list(
    self, mock_get_constants, mock_requests_get, mock_get_cache
  ):
    """Test jenkins_get_jobs with empty jobs list."""
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache

    mock_response = Mock()
    mock_response.json.return_value = {"jobs": []}
    mock_requests_get.return_value = mock_response

    mock_get_constants.return_value = {
      "JENKINS_URL": "http://test-jenkins.com",
      "JENKINS_USER": "user",
      "JENKINS_TOKEN": "token",
    }

    result = jenkins_get_jobs()
    assert result == []

  @patch("devops_mcps.utils.jenkins.jenkins_job_api._get_cache")
  @patch("devops_mcps.utils.jenkins.jenkins_job_api.requests.get")
  @patch("devops_mcps.utils.jenkins.jenkins_job_api._get_jenkins_constants")
  def test_jenkins_get_jobs_various_colors(
    self, mock_get_constants, mock_requests_get, mock_get_cache
  ):
    """Test jenkins_get_jobs with various color statuses."""
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache

    mock_response = Mock()
    mock_response.json.return_value = {
      "jobs": [
        {"name": "red-job", "color": "red"},
        {"name": "blue-job", "color": "blue"},
        {"name": "aborted-job", "color": "aborted"},
        {"name": "disabled-job", "color": "disabled"},
        {"name": "anime-job", "color": "blue_anime"},  # In progress
      ]
    }
    mock_requests_get.return_value = mock_response

    mock_get_constants.return_value = {
      "JENKINS_URL": "http://test-jenkins.com",
      "JENKINS_USER": "user",
      "JENKINS_TOKEN": "token",
    }

    result = jenkins_get_jobs()
    assert len(result) == 5

    # Check is_enabled status
    # "disabled" not in color -> enabled
    assert result[0]["is_enabled"] is True  # red
    assert result[1]["is_enabled"] is True  # blue
    assert result[2]["is_enabled"] is True  # aborted
    assert result[3]["is_enabled"] is False  # disabled
    assert result[4]["is_enabled"] is True  # blue_anime

  @patch("devops_mcps.utils.jenkins.jenkins_job_api._get_cache")
  @patch("devops_mcps.utils.jenkins.jenkins_job_api.requests.get")
  @patch("devops_mcps.utils.jenkins.jenkins_job_api._get_jenkins_constants")
  def test_jenkins_get_jobs_missing_fields(
    self, mock_get_constants, mock_requests_get, mock_get_cache
  ):
    """Test jenkins_get_jobs with missing fields in response."""
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_get_cache.return_value = mock_cache

    mock_response = Mock()
    # Job with missing url, color, lastBuild
    mock_response.json.return_value = {"jobs": [{"name": "minimal-job"}]}
    mock_requests_get.return_value = mock_response

    mock_get_constants.return_value = {
      "JENKINS_URL": "http://test-jenkins.com",
      "JENKINS_USER": "user",
      "JENKINS_TOKEN": "token",
    }

    result = jenkins_get_jobs()
    assert len(result) == 1
    job = result[0]
    assert job["name"] == "minimal-job"
    assert job["url"] is None
    assert job["is_enabled"] is True  # "disabled" not in "" -> True
    assert job["last_build_number"] is None
    assert job["last_build_url"] is None
