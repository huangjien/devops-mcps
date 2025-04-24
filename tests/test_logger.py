# tests/test_logger.py

import logging
import os
import pytest
from logging.handlers import RotatingFileHandler
from devops_mcps.logger import setup_logging, LOG_FILENAME

# --- Fixtures ---


@pytest.fixture(autouse=True)
def isolated_logger_state():
  """
  Ensures each test runs with a clean root logger state.
  Saves original handlers/level, clears root logger, runs test, restores state.
  """
  original_level = logging.root.level
  original_handlers = logging.root.handlers[:]  # Create a copy

  # Clear handlers before the test
  logging.root.handlers.clear()
  # Reset level to default before test configures it
  logging.root.setLevel(logging.WARNING)

  yield  # Run the test

  # Clear handlers added by the test
  logging.root.handlers.clear()

  # Restore original handlers and level
  for handler in original_handlers:
    logging.root.addHandler(handler)
  logging.root.setLevel(original_level)


@pytest.fixture
def cleanup_log_file():
  """Clean up log file after test."""
  yield
  if os.path.exists(LOG_FILENAME):
    os.remove(LOG_FILENAME)


# --- Tests ---


def test_setup_logging_creates_file_handler(isolated_logger_state, cleanup_log_file):
  """Test that setup_logging creates a file handler."""
  setup_logging()
  handlers = logging.root.handlers

  assert any(isinstance(h, RotatingFileHandler) for h in handlers)
  file_handler = next((h for h in handlers if isinstance(h, RotatingFileHandler)), None)
  assert file_handler is not None
  assert os.path.basename(file_handler.baseFilename) == LOG_FILENAME


def test_logging_to_file(isolated_logger_state, cleanup_log_file):
  """Test that logs are written to the log file."""
  setup_logging()
  logger = logging.getLogger(__name__)
  test_message = f"Test log message {os.urandom(4).hex()}"
  logger.info(test_message)

  # Ensure handlers flush
  for handler in logger.handlers:
    handler.flush()

  assert os.path.exists(LOG_FILENAME)
  with open(LOG_FILENAME, "r") as f:
    content = f.read()
  assert test_message in content


def test_log_level_respected(isolated_logger_state, cleanup_log_file):
  """Test that the log level is respected."""
  setup_logging()
  logger = logging.getLogger(__name__)

  test_debug_msg = f"This DEBUG should be logged {os.urandom(4).hex()}"
  test_info_msg = f"This INFO should be logged {os.urandom(4).hex()}"
  test_warn_msg = f"This WARNING should be logged {os.urandom(4).hex()}"

  logger.debug(test_debug_msg)
  logger.info(test_info_msg)
  logger.warning(test_warn_msg)

  assert os.path.exists(LOG_FILENAME)
  with open(LOG_FILENAME, "r") as f:
    content = f.read()
  assert test_debug_msg in content
  assert test_info_msg in content
  assert test_warn_msg in content


def test_log_format(isolated_logger_state, cleanup_log_file):
  """Test that log format is correct."""
  setup_logging()
  logger = logging.getLogger(__name__)
  test_message = f"Format test {os.urandom(4).hex()}"
  logger.info(test_message)

  for handler in logger.handlers:
    handler.flush()

  assert os.path.exists(LOG_FILENAME)
  with open(LOG_FILENAME, "r") as f:
    content = f.read()
  assert test_message in content
  assert "INFO" in content
  assert __name__ in content
