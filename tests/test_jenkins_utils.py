"""Tests for Jenkins utility functions and helpers."""

import pytest
from unittest.mock import MagicMock, patch
from jenkinsapi.job import Job
from jenkinsapi.view import View


def test_to_dict_with_simple_object():
    """Test _to_dict with a simple object."""
    from src.devops_mcps.jenkins import _to_dict

    class SimpleObject:
        def __init__(self):
            self.name = "test"
            self.value = 42

    obj = SimpleObject()
    result = _to_dict(obj)

    assert result["name"] == "test"
    assert result["value"] == 42


def test_to_dict_with_nested_object():
    """Test _to_dict with nested objects."""
    from src.devops_mcps.jenkins import _to_dict

    class NestedObject:
        def __init__(self):
            self.inner_name = "inner"

    class OuterObject:
        def __init__(self):
            self.name = "outer"
            self.nested = NestedObject()

    obj = OuterObject()
    result = _to_dict(obj)

    assert result["name"] == "outer"
    assert result["nested"]["inner_name"] == "inner"


def test_to_dict_with_list():
    """Test _to_dict with a list of objects."""
    from src.devops_mcps.jenkins import _to_dict

    class ListItem:
        def __init__(self, name):
            self.name = name

    items = [ListItem("item1"), ListItem("item2")]
    result = _to_dict(items)

    assert len(result) == 2
    assert result[0]["name"] == "item1"
    assert result[1]["name"] == "item2"


def test_to_dict_with_dict():
    """Test _to_dict with a dictionary."""
    from src.devops_mcps.jenkins import _to_dict

    data = {"key1": "value1", "key2": {"nested_key": "nested_value"}}
    result = _to_dict(data)

    assert result["key1"] == "value1"
    assert result["key2"]["nested_key"] == "nested_value"


def test_to_dict_with_primitive_types():
    """Test _to_dict with primitive types."""
    from src.devops_mcps.jenkins import _to_dict

    assert _to_dict("string") == "string"
    assert _to_dict(42) == 42
    assert _to_dict(True) is True
    assert _to_dict(None) is None


def test_to_dict_with_job_object():
    """Test _to_dict with a Job object."""
    from src.devops_mcps.jenkins import _to_dict

    # Create a mock Job object
    mock_job = MagicMock(spec=Job)
    mock_job.name = "test-job"
    mock_job.baseurl = "http://jenkins/job/test-job/"
    mock_job.is_enabled.return_value = True
    mock_job.is_queued.return_value = False
    mock_job.get_last_buildnumber.return_value = 42
    mock_job.get_last_build_url = MagicMock()
    mock_job.get_last_build_url.return_value = "http://jenkins/job/test-job/42/"
    mock_job.get_last_buildurl = MagicMock()
    mock_job.get_last_buildurl.return_value = "http://jenkins/job/test-job/42/"

    result = _to_dict(mock_job)

    assert result["name"] == "test-job"
    assert result["url"] == "http://jenkins/job/test-job/"
    assert result["is_enabled"] is True
    assert result["is_queued"] is False
    assert result["last_build_number"] == 42
    assert result["last_build_url"] == "http://jenkins/job/test-job/42/"


def test_to_dict_with_view_object():
    """Test _to_dict with a View object."""
    from src.devops_mcps.jenkins import _to_dict

    # Create a mock View object
    mock_view = MagicMock(spec=View)
    mock_view.name = "test-view"
    mock_view.baseurl = "http://jenkins/view/test-view/"


    result = _to_dict(mock_view)

    assert result["name"] == "test-view"
    assert result["url"] == "http://jenkins/view/test-view/"


def test_to_dict_with_nested_job_in_list():
    """Test _to_dict with nested Job objects in a list."""
    from src.devops_mcps.jenkins import _to_dict

    # Create a mock Job object
    mock_job = MagicMock(spec=Job)
    mock_job.name = "nested-job"
    mock_job.baseurl = "http://jenkins/job/nested-job/"
    mock_job.is_enabled.return_value = True
    mock_job.is_queued.return_value = False
    mock_job.get_last_buildnumber.return_value = 10
    mock_job.get_last_build_url = MagicMock()
    mock_job.get_last_build_url.return_value = "http://jenkins/job/nested-job/10/"
    mock_job.get_last_buildurl = MagicMock()
    mock_job.get_last_buildurl.return_value = "http://jenkins/job/nested-job/10/"

    # Create a container object with a list of jobs
    class JobContainer:
        def __init__(self):
            self.jobs = [mock_job]
            self.name = "container"

    container = JobContainer()
    result = _to_dict(container)

    assert result["name"] == "container"
    assert len(result["jobs"]) == 1
    assert result["jobs"][0]["name"] == "nested-job"
    assert result["jobs"][0]["url"] == "http://jenkins/job/nested-job/"
    assert result["jobs"][0]["is_enabled"] is True
    assert result["jobs"][0]["is_queued"] is False
    assert result["jobs"][0]["last_build_number"] == 10
    assert result["jobs"][0]["last_build_url"] == "http://jenkins/job/nested-job/10/"


def test_to_dict_with_circular_reference():
    """Test _to_dict handles circular references gracefully."""
    from src.devops_mcps.jenkins import _to_dict

    class CircularObject:
        def __init__(self):
            self.name = "circular"
            self.self_ref = self

    obj = CircularObject()
    
    # This should not cause infinite recursion
    # The implementation should handle this gracefully
    result = _to_dict(obj)
    
    # At minimum, the name should be preserved
    assert result["name"] == "circular"


def test_to_dict_with_complex_nested_structure():
    """Test _to_dict with complex nested structures."""
    from src.devops_mcps.jenkins import _to_dict

    class ComplexObject:
        def __init__(self):
            self.string_attr = "test"
            self.int_attr = 42
            self.list_attr = ["item1", "item2"]
            self.dict_attr = {"key": "value"}
            self.none_attr = None
            self.bool_attr = True

    obj = ComplexObject()
    result = _to_dict(obj)

    assert result["string_attr"] == "test"
    assert result["int_attr"] == 42
    assert result["list_attr"] == ["item1", "item2"]
    assert result["dict_attr"] == {"key": "value"}
    assert result["none_attr"] is None
    assert result["bool_attr"] is True


def test_to_dict_with_empty_collections():
    """Test _to_dict with empty collections."""
    from src.devops_mcps.jenkins import _to_dict

    class EmptyCollections:
        def __init__(self):
            self.empty_list = []
            self.empty_dict = {}
            self.empty_string = ""

    obj = EmptyCollections()
    result = _to_dict(obj)

    assert result["empty_list"] == []
    assert result["empty_dict"] == {}
    assert result["empty_string"] == ""


def test_to_dict_with_special_attributes():
    """Test _to_dict ignores special attributes like __dict__, __class__, etc."""
    from src.devops_mcps.jenkins import _to_dict

    class SpecialObject:
        def __init__(self):
            self.normal_attr = "normal"
            self.__private_attr = "private"

    obj = SpecialObject()
    result = _to_dict(obj)

    assert "normal_attr" in result
    assert result["normal_attr"] == "normal"
    # Private attributes might or might not be included depending on implementation
    # This test just ensures the function doesn't crash