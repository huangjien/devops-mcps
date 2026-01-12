"""Extended tests for logger module."""

import logging
import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import importlib

from devops_mcps import logger


class TestLoggerExtended(unittest.TestCase):
  """Extended test cases for logger module."""

  def setUp(self):
    """Set up test fixtures."""
    self.original_environ = os.environ.copy()
    # Reset logger module to ensure clean state
    importlib.reload(logger)

  def tearDown(self):
    """Clean up after tests."""
    os.environ.clear()
    os.environ.update(self.original_environ)

    # Clean up logging handlers
    root_logger = logging.getLogger()
    root_logger.handlers = []

    importlib.reload(logger)

  @patch("pathlib.Path.mkdir")
  @patch("devops_mcps.logger.LOG_FILENAME", "subdir/test.log")
  def test_log_dir_creation(self, mock_mkdir):
    """Test that directory is created if LOG_FILENAME has a directory component."""
    # We need to reload logger to pick up the patched LOG_FILENAME if it was a module level var
    # But LOG_FILENAME is calculated at module level.
    # So we need to patch os.environ before reload.

    with patch.dict(os.environ, {"LOG_FILENAME": "subdir/test.log"}):
      importlib.reload(logger)
      # Mock mkdir to avoid actual filesystem change
      with patch("pathlib.Path.mkdir") as mock_dir_mkdir:
        with patch("logging.handlers.RotatingFileHandler") as mock_handler_cls:
          # Configure mock handler
          mock_handler = mock_handler_cls.return_value
          mock_handler.level = logging.NOTSET

          logger.setup_logging()
          # The code checks if str(log_dir) != ".", so "subdir" should trigger mkdir
          mock_dir_mkdir.assert_called_once()

  def test_uncaught_exception_keyboard_interrupt(self):
    """Test that KeyboardInterrupt is handled by sys.__excepthook__."""
    # Setup logging to install excepthook
    with patch("logging.handlers.RotatingFileHandler") as mock_handler_cls:
      mock_handler = mock_handler_cls.return_value
      mock_handler.level = logging.NOTSET
      logger.setup_logging()

    # Mock sys.__excepthook__
    original_excepthook = sys.__excepthook__
    mock_excepthook = MagicMock()
    sys.__excepthook__ = mock_excepthook

    try:
      # Trigger the installed excepthook with KeyboardInterrupt
      # The excepthook is sys.excepthook
      sys.excepthook(KeyboardInterrupt, KeyboardInterrupt(), None)

      mock_excepthook.assert_called_once()
    finally:
      sys.__excepthook__ = original_excepthook

  def test_console_logging_enabled(self):
    """Test that console logging is enabled via environment variable."""
    with patch.dict(os.environ, {"MCP_CONSOLE_LOGGING": "true"}):
      # Reload to pick up env var
      importlib.reload(logger)

      with patch("logging.handlers.RotatingFileHandler") as mock_handler_cls:
        mock_handler = mock_handler_cls.return_value
        mock_handler.level = logging.NOTSET

        with patch("logging.Logger.info") as mock_info:
          logger.setup_logging()

          # Verify "Console (stderr)" is in the info log
          mock_info.assert_called()
          args = mock_info.call_args[0][0]
          self.assertIn("Console (stderr)", args)

  def test_console_logging_disabled_by_default(self):
    """Test that console logging is disabled by default."""
    # Ensure env var is not set
    if "MCP_CONSOLE_LOGGING" in os.environ:
      del os.environ["MCP_CONSOLE_LOGGING"]

    importlib.reload(logger)

    with patch("logging.handlers.RotatingFileHandler") as mock_handler_cls:
      mock_handler = mock_handler_cls.return_value
      mock_handler.level = logging.NOTSET

      with patch("logging.Logger.info") as mock_info:
        logger.setup_logging()

        # Verify "Console (stderr)" is NOT in the info log
        mock_info.assert_called()
        args = mock_info.call_args[0][0]
        self.assertNotIn("Console (stderr)", args)
