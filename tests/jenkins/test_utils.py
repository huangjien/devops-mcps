"""
Unit tests for Jenkins utils module.
"""

import unittest
from datetime import datetime

from devops_mcps.jenkins.utils import (
    _to_dict,
    format_timestamp,
    calculate_time_window,
    validate_job_name,
    validate_build_number
)


class TestJenkinsUtils(unittest.TestCase):
    """Test cases for Jenkins utility functions."""

    def test_to_dict_with_dict(self):
        """Test _to_dict with a dictionary input."""
        input_dict = {"key": "value", "number": 123}
        result = _to_dict(input_dict)
        self.assertEqual(result, input_dict)

    def test_to_dict_with_object(self):
        """Test _to_dict with an object that has __dict__."""
        class TestObject:
            def __init__(self):
                self.name = "test"
                self.value = 42
                
        obj = TestObject()
        result = _to_dict(obj)
        expected = {"name": "test", "value": 42}
        self.assertEqual(result, expected)

    def test_to_dict_with_object_without_dict(self):
        """Test _to_dict with an object without __dict__."""
        class TestObject:
            __slots__ = ['name', 'value']
            def __init__(self):
                self.name = "test"
                self.value = 42
                
        obj = TestObject()
        result = _to_dict(obj)
        expected = {"name": "test", "value": 42}
        self.assertEqual(result, expected)

    def test_to_dict_with_none(self):
        """Test _to_dict with None input."""
        result = _to_dict(None)
        self.assertIsNone(result)

    def test_to_dict_with_primitive(self):
        """Test _to_dict with primitive types."""
        self.assertEqual(_to_dict("string"), "string")
        self.assertEqual(_to_dict(123), 123)
        self.assertEqual(_to_dict(True), True)

    def test_to_dict_with_list(self):
        """Test _to_dict with a list."""
        input_list = [{"key": "value"}, "string", 123]
        result = _to_dict(input_list)
        self.assertEqual(result, input_list)

    def test_to_dict_with_nested_objects(self):
        """Test _to_dict with nested objects."""
        class NestedObject:
            def __init__(self):
                self.nested_value = "nested"
                
        class TestObject:
            def __init__(self):
                self.name = "test"
                self.nested = NestedObject()
                
        obj = TestObject()
        result = _to_dict(obj)
        expected = {
            "name": "test",
            "nested": {"nested_value": "nested"}
        }
        self.assertEqual(result, expected)

    def test_format_timestamp_valid(self):
        """Test format_timestamp with valid timestamp."""
        timestamp = 1640995200  # 2022-01-01 00:00:00 UTC
        result = format_timestamp(timestamp)
        self.assertEqual(result, "2022-01-01T00:00:00Z")

    def test_format_timestamp_none(self):
        """Test format_timestamp with None input."""
        result = format_timestamp(None)
        self.assertIsNone(result)

    def test_format_timestamp_zero(self):
        """Test format_timestamp with zero timestamp."""
        result = format_timestamp(0)
        self.assertEqual(result, "1970-01-01T00:00:00Z")

    def test_format_timestamp_negative(self):
        """Test format_timestamp with negative timestamp."""
        result = format_timestamp(-3600)
        self.assertEqual(result, "1969-12-31T23:00:00Z")

    def test_calculate_time_window_hours(self):
        """Test calculate_time_window with hours."""
        now = datetime(2023, 1, 1, 12, 0, 0)
        result = calculate_time_window(24, "hours", now=now)
        expected_start = datetime(2022, 12, 31, 12, 0, 0)
        expected_end = datetime(2023, 1, 1, 12, 0, 0)
        
        self.assertEqual(result["start_time"], expected_start)
        self.assertEqual(result["end_time"], expected_end)

    def test_calculate_time_window_days(self):
        """Test calculate_time_window with days."""
        now = datetime(2023, 1, 1, 12, 0, 0)
        result = calculate_time_window(7, "days", now=now)
        expected_start = datetime(2022, 12, 25, 12, 0, 0)
        expected_end = datetime(2023, 1, 1, 12, 0, 0)
        
        self.assertEqual(result["start_time"], expected_start)
        self.assertEqual(result["end_time"], expected_end)

    def test_calculate_time_window_weeks(self):
        """Test calculate_time_window with weeks."""
        now = datetime(2023, 1, 1, 12, 0, 0)
        result = calculate_time_window(2, "weeks", now=now)
        expected_start = datetime(2022, 12, 18, 12, 0, 0)
        expected_end = datetime(2023, 1, 1, 12, 0, 0)
        
        self.assertEqual(result["start_time"], expected_start)
        self.assertEqual(result["end_time"], expected_end)

    def test_calculate_time_window_invalid_unit(self):
        """Test calculate_time_window with invalid unit."""
        with self.assertRaises(ValueError):
            calculate_time_window(1, "invalid")

    def test_calculate_time_window_negative_value(self):
        """Test calculate_time_window with negative value."""
        with self.assertRaises(ValueError):
            calculate_time_window(-1, "hours")

    def test_calculate_time_window_zero_value(self):
        """Test calculate_time_window with zero value."""
        with self.assertRaises(ValueError):
            calculate_time_window(0, "hours")

    def test_validate_job_name_valid(self):
        """Test validate_job_name with valid names."""
        self.assertTrue(validate_job_name("test-job"))
        self.assertTrue(validate_job_name("test_job"))
        self.assertTrue(validate_job_name("test.job"))
        self.assertTrue(validate_job_name("test123"))
        self.assertTrue(validate_job_name("Test-Job"))

    def test_validate_job_name_invalid(self):
        """Test validate_job_name with invalid names."""
        self.assertFalse(validate_job_name(""))
        self.assertFalse(validate_job_name(None))
        self.assertFalse(validate_job_name("test job"))  # space
        self.assertFalse(validate_job_name("test@job"))  # special char
        self.assertFalse(validate_job_name("test/job"))  # slash
        self.assertFalse(validate_job_name("test\\job"))  # backslash

    def test_validate_job_name_too_long(self):
        """Test validate_job_name with very long name."""
        long_name = "a" * 256  # Exceeds typical limits
        self.assertFalse(validate_job_name(long_name))

    def test_validate_build_number_valid(self):
        """Test validate_build_number with valid numbers."""
        self.assertTrue(validate_build_number(1))
        self.assertTrue(validate_build_number(123))
        self.assertTrue(validate_build_number(9999))

    def test_validate_build_number_invalid(self):
        """Test validate_build_number with invalid numbers."""
        self.assertFalse(validate_build_number(-1))
        self.assertFalse(validate_build_number(None))
        self.assertFalse(validate_build_number("not_a_number"))

    def test_validate_build_number_float(self):
        """Test validate_build_number with float."""
        self.assertFalse(validate_build_number(1.5))

    def test_validate_build_number_very_large(self):
        """Test validate_build_number with very large number."""
        self.assertTrue(validate_build_number(1000000))  # Should be valid


if __name__ == '__main__':
    unittest.main()