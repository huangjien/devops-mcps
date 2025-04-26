# /Users/huangjien/workspace/devops-mcps/tests/test_logger.py
import logging
import os
from unittest import mock
import importlib  # Import importlib

import pytest

# Make sure to import the setup_logging function from your module
# Import the module itself to allow reloading
from devops_mcps import logger  # Adjust import path as needed


# Example using pytest fixture and mock.patch.dict
@pytest.fixture(autouse=True)
def reset_logging_and_env():
  """Ensure clean state for each test."""
  original_handlers = logging.root.handlers[:]
  original_level = logging.root.level

  logging.shutdown()  # Shut down existing handlers (might be redundant now but safe)
  logging.root.handlers.clear()  # Explicitly clear root handlers

  # Clear relevant env vars before each test
  env_vars_to_clear = ["LOG_LEVEL"]
  original_values = {var: os.environ.get(var) for var in env_vars_to_clear}
  for var in env_vars_to_clear:
    if var in os.environ:
      del os.environ[var]

  # --- Crucial: Reload logger module here to reset its initial state ---
  # This ensures the default LOG_LEVEL is re-evaluated based on the clean env
  importlib.reload(logger)

  yield  # Run the test

  # Restore original env vars
  for var, value in original_values.items():
    if value is None:
      if var in os.environ:
        del os.environ[var]
    else:
      os.environ[var] = value

  # --- Reload logger module again after test to reflect restored env (optional but good practice) ---
  importlib.reload(logger)

  # Restore original logging state
  logging.shutdown()
  logging.root.handlers.clear()
  logging.root.setLevel(original_level)
  for handler in original_handlers:
    logging.root.addHandler(handler)


def test_logger_default_level_info():
  """Test that default log level is INFO when LOG_LEVEL env var is not set."""
  # Env var is cleared by the fixture, logger module is reloaded by fixture
  logger.setup_logging()
  root_logger = logging.getLogger()
  # Check the level set by setup_logging
  assert root_logger.level == logging.INFO
  # Also check the module constant determined
  assert logger.LOG_LEVEL == logging.INFO


def test_logger_level_debug_from_env():
  """Test setting log level to DEBUG via environment variable."""
  with mock.patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
    # --- Reload the logger module AFTER patching env ---
    importlib.reload(logger)
    # Check the module constant determined
    assert logger.LOG_LEVEL == logging.DEBUG
    logger.setup_logging()  # Call setup *after* reloading
  root_logger = logging.getLogger()
  # Check the level set by setup_logging
  assert root_logger.level == logging.DEBUG


def test_logger_level_warning_case_insensitive():
  """Test setting log level case-insensitively."""
  with mock.patch.dict(os.environ, {"LOG_LEVEL": "warning"}):
    # --- Reload the logger module AFTER patching env ---
    importlib.reload(logger)
    # Check the module constant determined
    assert logger.LOG_LEVEL == logging.WARNING
    logger.setup_logging()
  root_logger = logging.getLogger()
  # Check the level set by setup_logging
  assert root_logger.level == logging.WARNING


@mock.patch("logging.Logger.warning")
def test_logger_invalid_level_defaults_to_info(mock_logger_warning):  # Inject mock
  """Test that an invalid LOG_LEVEL defaults to INFO and logs a warning."""
  with mock.patch.dict(os.environ, {"LOG_LEVEL": "INVALID_LEVEL"}):
    # Reload the logger module AFTER patching env
    importlib.reload(logger)

    # 1. Assert that the module correctly determined INFO as the level
    assert logger.LOG_LEVEL == logging.INFO

    # Call setup_logging - this should trigger the internal warning call
    logger.setup_logging()

    # 2. Assert the root logger level was actually set to INFO by setup_logging
    root_logger = logging.getLogger()
    assert root_logger.level == logging.INFO

    # 3. Assert that the 'warning' method was called with the expected message.
    #    We check the call arguments passed to the mock.
    found_call = False
    expected_msg_part1 = "Invalid LOG_LEVEL 'INVALID_LEVEL'"
    expected_msg_part2 = "Defaulting to 'INFO'"
    for call in mock_logger_warning.call_args_list:
      args, _ = call  # Get positional arguments of the call
      if args and isinstance(args[0], str):  # Check if first arg is a string
        if expected_msg_part1 in args[0] and expected_msg_part2 in args[0]:
          found_call = True
          break
    assert found_call, (
      f"Expected warning containing '{expected_msg_part1}' and '{expected_msg_part2}' was not logged."
    )

    # Optional simpler check if only one warning call is expected on any logger:
    # mock_logger_warning.assert_called_once()
    # call_args, _ = mock_logger_warning.call_args
    # assert expected_msg_part1 in call_args[0]
    # assert expected_msg_part2 in call_args[0]


# Add more tests for file handler creation, rotation (might need mock_open), etc.
# Example: Test file handler creation (requires mocking file operations)
@mock.patch("logging.handlers.RotatingFileHandler", autospec=True)
def test_file_handler_setup(mock_rotating_handler):
  """Test that the RotatingFileHandler is configured."""

  # --- Start Fix for Failure 2 ---
  # Configure the mock instance returned by the handler constructor
  mock_handler_instance = mock_rotating_handler.return_value
  # Set the 'level' attribute that the logging system expects
  mock_handler_instance.level = logging.NOTSET  # Default handler level
  # --- End Fix for Failure 2 ---

  # Ensure LOG_LEVEL is something valid for this test if needed
  with mock.patch.dict(os.environ, {"LOG_LEVEL": "INFO"}):
    importlib.reload(logger)
    # Check module level constant
    assert logger.LOG_LEVEL == logging.INFO
    success = logger.setup_logging()

  assert success is True
  mock_rotating_handler.assert_called_once()
  # Check some args used during initialization
  args, kwargs = mock_rotating_handler.call_args
  assert kwargs.get("filename") == logger.LOG_FILENAME
  assert kwargs.get("maxBytes") == logger.MAX_BYTES
  assert kwargs.get("backupCount") == logger.BACKUP_COUNT
  assert kwargs.get("encoding") == "utf-8"

  # Check if handler was added to root logger
  root_logger = logging.getLogger()
  assert mock_handler_instance in root_logger.handlers
  # Check if formatter was set
  mock_handler_instance.setFormatter.assert_called_once_with(logger.log_formatter)
