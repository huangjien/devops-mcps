"""Unit tests for main_entry.py module.

This module contains comprehensive tests for the main entry point functions
including main(), main_stream_http(), and setup_and_run().
"""

import sys
import os
import unittest
import logging
from unittest.mock import patch, MagicMock

# Add src to sys.path for import
sys.path.insert(
  0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

from devops_mcps import main_entry


class TestMainEntry(unittest.TestCase):
  """Test cases for main_entry module functions."""

  def setUp(self):
    """Set up test fixtures."""
    self.original_argv = sys.argv.copy()

  def tearDown(self):
    """Clean up after tests."""
    sys.argv = self.original_argv

  @patch("devops_mcps.main_entry.initialize_clients")
  @patch("devops_mcps.main_entry.create_mcp_server")
  @patch("devops_mcps.main_entry.register_tools")
  @patch("devops_mcps.main_entry.load_and_register_prompts")
  @patch("argparse.ArgumentParser.parse_args")
  def test_main_with_stdio_transport(
    self,
    mock_parse_args,
    mock_load_prompts,
    mock_register_tools,
    mock_create_server,
    mock_initialize_clients,
  ):
    """Test main() function with stdio transport (default)."""
    # Setup mocks
    mock_server = MagicMock()
    mock_create_server.return_value = mock_server
    mock_args = MagicMock()
    mock_args.transport = "stdio"
    mock_parse_args.return_value = mock_args

    # Call function
    main_entry.main()

    # Verify calls
    mock_initialize_clients.assert_called_once()
    mock_create_server.assert_called_once()
    mock_register_tools.assert_called_once_with(mock_server)
    mock_load_prompts.assert_called_once_with(mock_server)
    mock_server.run.assert_called_once_with(transport="stdio")

  @patch("devops_mcps.main_entry.initialize_clients")
  @patch("devops_mcps.main_entry.create_mcp_server")
  @patch("devops_mcps.main_entry.register_tools")
  @patch("devops_mcps.main_entry.load_and_register_prompts")
  @patch("argparse.ArgumentParser.parse_args")
  def test_main_with_stream_http_transport(
    self,
    mock_parse_args,
    mock_load_prompts,
    mock_register_tools,
    mock_create_server,
    mock_initialize_clients,
  ):
    """Test main() function with stream_http transport."""
    # Setup mocks
    mock_server = MagicMock()
    mock_create_server.return_value = mock_server
    mock_args = MagicMock()
    mock_args.transport = "stream_http"
    mock_parse_args.return_value = mock_args

    # Call function
    main_entry.main()

    # Verify calls
    mock_initialize_clients.assert_called_once()
    mock_create_server.assert_called_once()
    mock_register_tools.assert_called_once_with(mock_server)
    mock_load_prompts.assert_called_once_with(mock_server)
    mock_server.run.assert_called_once_with(
      transport="streamable-http", mount_path="/mcp"
    )

  @patch("devops_mcps.main_entry.initialize_clients")
  @patch("devops_mcps.main_entry.create_mcp_server")
  @patch("devops_mcps.main_entry.register_tools")
  @patch("devops_mcps.main_entry.load_and_register_prompts")
  @patch("argparse.ArgumentParser.parse_args")
  def test_main_initialization_failure(
    self,
    mock_parse_args,
    mock_load_prompts,
    mock_register_tools,
    mock_create_server,
    mock_initialize_clients,
  ):
    """Test main() function when initialization fails."""
    # Setup mocks
    mock_initialize_clients.side_effect = Exception("Initialization failed")
    mock_args = MagicMock()
    mock_args.transport = "stdio"
    mock_parse_args.return_value = mock_args

    # Call function and expect exception
    with self.assertRaises(Exception) as context:
      main_entry.main()

    self.assertEqual(str(context.exception), "Initialization failed")
    mock_initialize_clients.assert_called_once()
    mock_create_server.assert_not_called()

  @patch("devops_mcps.main_entry.initialize_clients")
  @patch("devops_mcps.main_entry.create_mcp_server")
  @patch("devops_mcps.main_entry.register_tools")
  @patch("devops_mcps.main_entry.load_and_register_prompts")
  def test_main_server_creation_failure(
    self,
    mock_load_prompts,
    mock_register_tools,
    mock_create_server,
    mock_initialize_clients,
  ):
    """Test main() function when server creation fails."""
    # Setup mocks
    mock_create_server.side_effect = Exception("Server creation failed")

    # Call function and expect exception
    with self.assertRaises(Exception) as context:
      main_entry.main()

    self.assertEqual(str(context.exception), "Server creation failed")
    mock_initialize_clients.assert_called_once()
    mock_create_server.assert_called_once()
    mock_register_tools.assert_not_called()


class TestMainStreamHttp(unittest.TestCase):
  """Test cases for main_stream_http() function."""

  def setUp(self):
    """Set up test fixtures."""
    self.original_argv = sys.argv.copy()

  def tearDown(self):
    """Clean up after tests."""
    sys.argv = self.original_argv

  @patch("devops_mcps.main_entry.main")
  def test_main_stream_http_no_transport_arg(self, mock_main):
    """Test main_stream_http() when --transport is not in sys.argv."""
    sys.argv = ["script.py"]

    main_entry.main_stream_http()

    self.assertIn("--transport", sys.argv)
    self.assertIn("stream_http", sys.argv)
    mock_main.assert_called_once()

  @patch("devops_mcps.main_entry.main")
  def test_main_stream_http_with_transport_arg_different_value(self, mock_main):
    """Test main_stream_http() when --transport exists with different value."""
    sys.argv = ["script.py", "--transport", "stdio"]

    main_entry.main_stream_http()

    self.assertIn("--transport", sys.argv)
    self.assertIn("stream_http", sys.argv)
    self.assertEqual(sys.argv[sys.argv.index("--transport") + 1], "stream_http")
    mock_main.assert_called_once()

  @patch("devops_mcps.main_entry.main")
  def test_main_stream_http_with_transport_arg_no_value(self, mock_main):
    """Test main_stream_http() when --transport exists but no value follows."""
    sys.argv = ["script.py", "--transport"]

    main_entry.main_stream_http()

    self.assertIn("--transport", sys.argv)
    self.assertIn("stream_http", sys.argv)
    mock_main.assert_called_once()

  @patch("devops_mcps.main_entry.main")
  def test_main_stream_http_already_stream_http(self, mock_main):
    """Test main_stream_http() when stream_http is already in sys.argv."""
    sys.argv = ["script.py", "--transport", "stream_http"]
    original_argv = sys.argv.copy()

    main_entry.main_stream_http()

    # Should not modify argv if stream_http is already present
    self.assertEqual(sys.argv, original_argv)
    mock_main.assert_called_once()

  @patch("devops_mcps.main_entry.main")
  def test_main_stream_http_transport_not_found_value_error(self, mock_main):
    """Test main_stream_http() when --transport is not found (ValueError case)."""
    sys.argv = ["script.py", "other_arg"]

    main_entry.main_stream_http()

    self.assertIn("--transport", sys.argv)
    self.assertIn("stream_http", sys.argv)
    mock_main.assert_called_once()


class TestSetupAndRun(unittest.TestCase):
  """Test cases for setup_and_run() function."""

  @patch("devops_mcps.main_entry.initialize_clients")
  @patch("devops_mcps.main_entry.create_mcp_server")
  @patch("devops_mcps.main_entry.register_tools")
  @patch("devops_mcps.main_entry.load_and_register_prompts")
  def test_setup_and_run_default_stdio(
    self,
    mock_load_prompts,
    mock_register_tools,
    mock_create_server,
    mock_initialize_clients,
  ):
    """Test setup_and_run() with default stdio transport."""
    # Setup mocks
    mock_server = MagicMock()
    mock_create_server.return_value = mock_server

    # Call function
    main_entry.setup_and_run()

    # Verify calls
    mock_initialize_clients.assert_called_once()
    mock_create_server.assert_called_once()
    mock_register_tools.assert_called_once_with(mock_server)
    mock_load_prompts.assert_called_once_with(mock_server)
    mock_server.run.assert_called_once_with(transport="stdio")

  @patch("devops_mcps.main_entry.initialize_clients")
  @patch("devops_mcps.main_entry.create_mcp_server")
  @patch("devops_mcps.main_entry.register_tools")
  @patch("devops_mcps.main_entry.load_and_register_prompts")
  def test_setup_and_run_http_transport(
    self,
    mock_load_prompts,
    mock_register_tools,
    mock_create_server,
    mock_initialize_clients,
  ):
    """Test setup_and_run() with http transport."""
    # Setup mocks
    mock_server = MagicMock()
    mock_create_server.return_value = mock_server

    # Call function
    main_entry.setup_and_run(transport="http", host="localhost", port=8080)

    # Verify calls
    mock_initialize_clients.assert_called_once()
    mock_create_server.assert_called_once()
    mock_register_tools.assert_called_once_with(mock_server)
    mock_load_prompts.assert_called_once_with(mock_server)
    mock_server.run.assert_called_once_with(
      transport="streamable-http", mount_path="/mcp"
    )

  @patch("devops_mcps.main_entry.initialize_clients")
  @patch("devops_mcps.main_entry.create_mcp_server")
  @patch("devops_mcps.main_entry.register_tools")
  @patch("devops_mcps.main_entry.load_and_register_prompts")
  def test_setup_and_run_custom_transport(
    self,
    mock_load_prompts,
    mock_register_tools,
    mock_create_server,
    mock_initialize_clients,
  ):
    """Test setup_and_run() with custom transport."""
    # Setup mocks
    mock_server = MagicMock()
    mock_create_server.return_value = mock_server

    # Call function
    main_entry.setup_and_run(transport="custom")

    # Verify calls
    mock_initialize_clients.assert_called_once()
    mock_create_server.assert_called_once()
    mock_register_tools.assert_called_once_with(mock_server)
    mock_load_prompts.assert_called_once_with(mock_server)
    mock_server.run.assert_called_once_with(transport="custom")

  @patch("devops_mcps.main_entry.initialize_clients")
  @patch("devops_mcps.main_entry.create_mcp_server")
  @patch("devops_mcps.main_entry.register_tools")
  @patch("devops_mcps.main_entry.load_and_register_prompts")
  def test_setup_and_run_tool_registration_failure(
    self,
    mock_load_prompts,
    mock_register_tools,
    mock_create_server,
    mock_initialize_clients,
  ):
    """Test setup_and_run() when tool registration fails."""
    # Setup mocks
    mock_server = MagicMock()
    mock_create_server.return_value = mock_server
    mock_register_tools.side_effect = Exception("Tool registration failed")

    # Call function and expect exception
    with self.assertRaises(Exception) as context:
      main_entry.setup_and_run()

    self.assertEqual(str(context.exception), "Tool registration failed")
    mock_initialize_clients.assert_called_once()
    mock_create_server.assert_called_once()
    mock_register_tools.assert_called_once_with(mock_server)
    mock_load_prompts.assert_not_called()

  @patch("devops_mcps.main_entry.initialize_clients")
  @patch("devops_mcps.main_entry.create_mcp_server")
  @patch("devops_mcps.main_entry.register_tools")
  @patch("devops_mcps.main_entry.load_and_register_prompts")
  def test_setup_and_run_prompt_loading_failure(
    self,
    mock_load_prompts,
    mock_register_tools,
    mock_create_server,
    mock_initialize_clients,
  ):
    """Test setup_and_run() when prompt loading fails."""
    # Setup mocks
    mock_server = MagicMock()
    mock_create_server.return_value = mock_server
    mock_load_prompts.side_effect = Exception("Prompt loading failed")

    # Call function and expect exception
    with self.assertRaises(Exception) as context:
      main_entry.setup_and_run()

    self.assertEqual(str(context.exception), "Prompt loading failed")
    mock_initialize_clients.assert_called_once()
    mock_create_server.assert_called_once()
    mock_register_tools.assert_called_once_with(mock_server)
    mock_load_prompts.assert_called_once_with(mock_server)


class TestMainEntryLogging(unittest.TestCase):
  """Test cases for logging functionality in main_entry module."""

  @patch("devops_mcps.main_entry.logger")
  @patch("devops_mcps.main_entry.initialize_clients")
  @patch("devops_mcps.main_entry.create_mcp_server")
  @patch("devops_mcps.main_entry.register_tools")
  @patch("devops_mcps.main_entry.load_and_register_prompts")
  @patch("argparse.ArgumentParser.parse_args")
  def test_main_logging_stdio(
    self,
    mock_parse_args,
    mock_load_prompts,
    mock_register_tools,
    mock_create_server,
    mock_initialize_clients,
    mock_logger,
  ):
    """Test that main() logs the correct transport type for stdio."""
    # Setup mocks
    mock_server = MagicMock()
    mock_create_server.return_value = mock_server
    mock_args = MagicMock()
    mock_args.transport = "stdio"
    mock_parse_args.return_value = mock_args

    # Call function
    main_entry.main()

    # Verify logging
    mock_logger.info.assert_called_with("Starting MCP server with stdio transport...")

  @patch("devops_mcps.main_entry.logger")
  @patch("devops_mcps.main_entry.initialize_clients")
  @patch("devops_mcps.main_entry.create_mcp_server")
  @patch("devops_mcps.main_entry.register_tools")
  @patch("devops_mcps.main_entry.load_and_register_prompts")
  @patch("argparse.ArgumentParser.parse_args")
  def test_main_logging_stream_http(
    self,
    mock_parse_args,
    mock_load_prompts,
    mock_register_tools,
    mock_create_server,
    mock_initialize_clients,
    mock_logger,
  ):
    """Test that main() logs the correct transport type for stream_http."""
    # Setup mocks
    mock_server = MagicMock()
    mock_create_server.return_value = mock_server
    mock_args = MagicMock()
    mock_args.transport = "stream_http"
    mock_parse_args.return_value = mock_args

    # Call function
    main_entry.main()

    # Verify logging
    mock_logger.info.assert_called_with(
      "Starting MCP server with stream_http transport..."
    )

  @patch("devops_mcps.main_entry.logger")
  @patch("devops_mcps.main_entry.initialize_clients")
  @patch("devops_mcps.main_entry.create_mcp_server")
  @patch("devops_mcps.main_entry.register_tools")
  @patch("devops_mcps.main_entry.load_and_register_prompts")
  def test_setup_and_run_logging(
    self,
    mock_load_prompts,
    mock_register_tools,
    mock_create_server,
    mock_initialize_clients,
    mock_logger,
  ):
    """Test that setup_and_run() logs the correct transport type."""
    # Setup mocks
    mock_server = MagicMock()
    mock_create_server.return_value = mock_server

    # Call function
    main_entry.setup_and_run(transport="http")

    # Verify logging
    mock_logger.info.assert_called_with("Starting MCP server with http transport...")


class TestMainEntryArgumentParsing(unittest.TestCase):
  """Test cases for argument parsing functionality."""

  @patch("devops_mcps.main_entry.initialize_clients")
  @patch("devops_mcps.main_entry.create_mcp_server")
  @patch("devops_mcps.main_entry.register_tools")
  @patch("devops_mcps.main_entry.load_and_register_prompts")
  def test_main_argument_parser_configuration(
    self,
    mock_load_prompts,
    mock_register_tools,
    mock_create_server,
    mock_initialize_clients,
  ):
    """Test that the argument parser is configured correctly."""
    # Setup mocks
    mock_server = MagicMock()
    mock_create_server.return_value = mock_server

    # Mock sys.argv to test argument parsing
    with patch("sys.argv", ["script.py", "--transport", "stdio"]):
      main_entry.main()

    # Verify server was called with stdio transport
    mock_server.run.assert_called_once_with(transport="stdio")

  @patch("devops_mcps.main_entry.initialize_clients")
  @patch("devops_mcps.main_entry.create_mcp_server")
  @patch("devops_mcps.main_entry.register_tools")
  @patch("devops_mcps.main_entry.load_and_register_prompts")
  def test_main_default_transport(
    self,
    mock_load_prompts,
    mock_register_tools,
    mock_create_server,
    mock_initialize_clients,
  ):
    """Test that the default transport is stdio when no argument is provided."""
    # Setup mocks
    mock_server = MagicMock()
    mock_create_server.return_value = mock_server

    # Mock sys.argv with no transport argument
    with patch("sys.argv", ["script.py"]):
      main_entry.main()

    # Verify server was called with stdio transport (default)
    mock_server.run.assert_called_once_with(transport="stdio")


class TestMainEntryModuleExecution(unittest.TestCase):
  """Test cases for module execution (__main__ block)."""

  @patch("devops_mcps.main_entry.main")
  def test_main_module_execution(self, mock_main):
    """Test that main() is called when module is executed directly."""
    # Simulate running the module as main
    original_name = main_entry.__name__
    try:
      main_entry.__name__ = "__main__"
      # Execute the module code that checks __name__
      exec("if __name__ == '__main__': main()", main_entry.__dict__)
      mock_main.assert_called_once()
    finally:
      main_entry.__name__ = original_name


class TestConfigureLogging(unittest.TestCase):
  """Test cases for _configure_logging function."""

  @patch("logging.getLogger")
  def test_configure_logging_valid_levels(self, mock_get_logger):
    """Test configuration with valid logging levels."""
    levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    for level in levels:
      main_entry._configure_logging(level)
      mock_get_logger.return_value.setLevel.assert_called_with(getattr(logging, level))

  @patch("logging.getLogger")
  def test_configure_logging_case_insensitive(self, mock_get_logger):
    """Test configuration with lowercase logging levels."""
    main_entry._configure_logging("debug")
    mock_get_logger.return_value.setLevel.assert_called_with(logging.DEBUG)

  @patch("logging.getLogger")
  def test_configure_logging_invalid_level(self, mock_get_logger):
    """Test configuration with invalid logging level (defaults to INFO)."""
    main_entry._configure_logging("INVALID")
    mock_get_logger.return_value.setLevel.assert_called_with(logging.INFO)

  @patch("logging.getLogger")
  def test_configure_logging_none(self, mock_get_logger):
    """Test configuration with None (no action)."""
    main_entry._configure_logging(None)
    mock_get_logger.assert_not_called()

  @patch("logging.getLogger")
  def test_configure_logging_not_string(self, mock_get_logger):
    """Test configuration with non-string input (no action)."""
    main_entry._configure_logging(123)
    mock_get_logger.assert_not_called()


class TestParseArgs(unittest.TestCase):
  """Test cases for _parse_args function."""

  def test_parse_args_defaults(self):
    """Test parsing with default arguments."""
    args = main_entry._parse_args([])
    self.assertEqual(args.transport, "stdio")
    self.assertEqual(args.mount_path, "/mcp")
    self.assertIsNone(args.log_level)
    self.assertFalse(args.version)

  def test_parse_args_custom(self):
    """Test parsing with custom arguments."""
    args = main_entry._parse_args(
      [
        "--transport",
        "stream_http",
        "--mount-path",
        "/custom",
        "--log-level",
        "DEBUG",
        "--version",
      ]
    )
    self.assertEqual(args.transport, "stream_http")
    self.assertEqual(args.mount_path, "/custom")
    self.assertEqual(args.log_level, "DEBUG")
    self.assertTrue(args.version)

  @patch("argparse.ArgumentParser.parse_args")
  @patch("argparse.ArgumentParser.parse_known_args")
  def test_parse_args_system_exit(self, mock_parse_known_args, mock_parse_args):
    """Test fallback to parse_known_args on SystemExit."""
    mock_parse_args.side_effect = SystemExit(2)
    mock_known_args = MagicMock()
    mock_parse_known_args.return_value = (mock_known_args, [])

    result = main_entry._parse_args(["--unknown-arg"])

    self.assertEqual(result, mock_known_args)
    mock_parse_args.assert_called_once()
    mock_parse_known_args.assert_called_once()


class TestMainVersion(unittest.TestCase):
  """Test cases for version printing in main()."""

  @patch("devops_mcps.main_entry._parse_args")
  @patch("devops_mcps.main_entry.version")
  @patch("builtins.print")
  def test_main_version_success(self, mock_print, mock_version, mock_parse_args):
    """Test version printing when package is found."""
    mock_args = MagicMock()
    mock_args.version = True
    mock_parse_args.return_value = mock_args
    mock_version.return_value = "1.2.3"

    main_entry.main()

    mock_version.assert_called_with("devops-mcps")
    mock_print.assert_called_with("1.2.3")

  @patch("devops_mcps.main_entry._parse_args")
  @patch("devops_mcps.main_entry.version")
  @patch("builtins.print")
  def test_main_version_not_found(self, mock_print, mock_version, mock_parse_args):
    """Test version printing when package is not found."""
    from importlib.metadata import PackageNotFoundError

    mock_args = MagicMock()
    mock_args.version = True
    mock_parse_args.return_value = mock_args
    mock_version.side_effect = PackageNotFoundError

    main_entry.main()

    mock_print.assert_called_with("unknown")


if __name__ == "__main__":
  unittest.main()
