"""
Jenkins utility functions and helper methods.
Includes common utilities used across Jenkins modules.
"""

from typing import Any, Dict, List, Union
from datetime import datetime, timezone, timedelta

from jenkinsapi.job import Job
from jenkinsapi.view import View


def _to_dict(obj: Any) -> Union[Dict[str, Any], List[Dict[str, Any]], Any]:
    """
    Convert Jenkins API objects to dictionaries recursively.
    
    Args:
        obj: Jenkins API object to convert
        
    Returns:
        Dictionary representation of the object, or the original object if conversion fails
    """
    if obj is None:
        return None
    
    # Handle built-in types
    if isinstance(obj, (str, int, float, bool)):
        return obj
    
    # Handle lists and tuples
    if isinstance(obj, (list, tuple)):
        return [_to_dict(item) for item in obj]
    
    # Handle dictionaries
    if isinstance(obj, dict):
        return {key: _to_dict(value) for key, value in obj.items()}
    
    # Handle Jenkins Job objects with specific key mappings
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
    
    # Handle Jenkins View objects with specific key mappings
    if isinstance(obj, View):
        return {"name": obj.name, "url": obj.baseurl, "description": obj.get_description()}
    
    # Handle objects with __dict__ attribute
    if hasattr(obj, '__dict__') and obj.__dict__:
        return {key: _to_dict(value) for key, value in obj.__dict__.items()}
    
    # Handle objects with __slots__
    if hasattr(obj, '__slots__'):
        slots_dict = {slot: _to_dict(getattr(obj, slot)) for slot in obj.__slots__ if hasattr(obj, slot)}
        if slots_dict:
            return slots_dict
    
    # For all other objects, return string representation
    try:
        return str(obj)
    except Exception:
        # If str() fails, return error message
        return f"<Error serializing object of type {type(obj).__name__}>"


def format_timestamp(timestamp: int) -> str:
    """
    Format timestamp to ISO format string.
    
    Args:
        timestamp: Timestamp in seconds (or milliseconds if > 1e10)
        
    Returns:
        ISO formatted timestamp string, or None if input is None/empty
    """
    if timestamp is None:
        return None
    
    if timestamp == 0:
        # Handle zero timestamp specifically
        timestamp_seconds = 0
    elif not timestamp:
        return ""
    
    try:
        # Handle both seconds and milliseconds timestamps
        if timestamp > 1e10:  # Likely milliseconds
            timestamp_seconds = timestamp / 1000.0
        else:  # Likely seconds
            timestamp_seconds = timestamp
        
        dt = datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc)
        # Return in simplified ISO format (without microseconds)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError):
        return ""


def calculate_time_window(value: int, unit: str, now: datetime = None) -> Dict[str, datetime]:
    """
    Calculate time window for time-based queries.
    
    Args:
        value: Number of time units to look back
        unit: Time unit ('hours', 'days', 'weeks')
        now: Optional reference datetime (defaults to current time)
        
    Returns:
        Dictionary with 'start_time' and 'end_time' datetime objects
        
    Raises:
        ValueError: If value is negative/zero or unit is invalid
    """
    if value <= 0:
        raise ValueError("Value must be positive")
    
    if now is None:
        now = datetime.now(timezone.utc)
    
    if unit == "hours":
        delta = timedelta(hours=value)
    elif unit == "days":
        delta = timedelta(days=value)
    elif unit == "weeks":
        delta = timedelta(weeks=value)
    else:
        raise ValueError(f"Invalid unit: {unit}")
    
    start_time = now - delta
    
    return {
        "start_time": start_time,
        "end_time": now
    }


def validate_job_name(job_name: str) -> bool:
    """
    Validate Jenkins job name format.
    
    Args:
        job_name: Job name to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not job_name or not isinstance(job_name, str):
        return False
    
    # Jenkins job names have restrictions:
    # - No spaces
    # - No special characters except: - _ .
    # - Maximum length is typically 255 characters
    # - Cannot be empty
    
    # Check length
    if len(job_name) > 255:
        return False
    
    # Check for invalid characters
    import re
    # Allow alphanumeric, hyphen, underscore, and dot
    if not re.match(r'^[a-zA-Z0-9_\-\.]+$', job_name):
        return False
    
    # Additional checks for specific invalid patterns
    invalid_patterns = [
        ' ',  # space
        '@',  # at sign
        '#',  # hash
        '$',  # dollar
        '%',  # percent
        '^',  # caret
        '&',  # ampersand
        '*',  # asterisk
        '(',  # open paren
        ')',  # close paren
        '+',  # plus
        '=',  # equals
        '[',  # open bracket
        ']',  # close bracket
        '{',  # open brace
        '}',  # close brace
        '|',  # pipe
        ';',  # semicolon
        ':',  # colon
        '"',  # double quote
        "'",  # single quote
        '<',  # less than
        '>',  # greater than
        ',',  # comma
        '?',  # question mark
        '/',  # forward slash
        '\\', # backslash
        '`',  # backtick
        '~',  # tilde
        '!',  # exclamation
    ]
    
    if any(pattern in job_name for pattern in invalid_patterns):
        return False
    
    return True


def validate_build_number(build_number: int) -> bool:
    """
    Validate that a build number is a non-negative integer.
    
    Args:
        build_number: The build number to validate
        
    Returns:
        True if valid, False otherwise
    """
    return isinstance(build_number, int) and build_number >= 0