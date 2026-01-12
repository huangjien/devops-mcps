"""Extended tests for main_entry module."""

import sys
import unittest
from unittest.mock import MagicMock, patch
import subprocess
import os

from devops_mcps import main_entry


class TestMainEntryExtended(unittest.TestCase):
  """Extended test cases for main_entry module."""

  @patch("devops_mcps.main_entry.logger")
  @patch("devops_mcps.main_entry.create_mcp_server")
  @patch("devops_mcps.main_entry.initialize_clients")
  @patch("devops_mcps.main_entry.register_tools")
  @patch("devops_mcps.main_entry.load_and_register_prompts")
  @patch("argparse.ArgumentParser.parse_args")
  def test_main_keyboard_interrupt(
    self,
    mock_parse_args,
    mock_load_prompts,
    mock_register_tools,
    mock_initialize_clients,
    mock_create_server,
    mock_logger,
  ):
    """Test main() handling of KeyboardInterrupt."""
    mock_args = MagicMock()
    mock_args.transport = "stdio"
    mock_parse_args.return_value = mock_args

    mock_server = MagicMock()
    mock_server.run.side_effect = KeyboardInterrupt()
    mock_create_server.return_value = mock_server

    with self.assertRaises(KeyboardInterrupt):
      main_entry.main()

    # Verify logger was called
    mock_logger.info.assert_called_with(
      "MCP server interrupted by user (KeyboardInterrupt). Shutting down."
    )

  @patch("devops_mcps.main_entry.logger")
  @patch("devops_mcps.main_entry.create_mcp_server")
  @patch("devops_mcps.main_entry.initialize_clients")
  @patch("devops_mcps.main_entry.register_tools")
  @patch("devops_mcps.main_entry.load_and_register_prompts")
  @patch("argparse.ArgumentParser.parse_args")
  def test_main_generic_exception(
    self,
    mock_parse_args,
    mock_load_prompts,
    mock_register_tools,
    mock_initialize_clients,
    mock_create_server,
    mock_logger,
  ):
    """Test main() handling of generic Exception."""
    mock_args = MagicMock()
    mock_args.transport = "stdio"
    mock_parse_args.return_value = mock_args

    mock_server = MagicMock()
    error = Exception("Unexpected error")
    mock_server.run.side_effect = error
    mock_create_server.return_value = mock_server

    with self.assertRaises(Exception):
      main_entry.main()

    # Verify logger was called
    mock_logger.error.assert_called()
    args = mock_logger.error.call_args[0]
    self.assertIn("MCP server failed to start", args[0])

  @patch("devops_mcps.main_entry.create_mcp_server")
  @patch("devops_mcps.main_entry.initialize_clients")
  @patch("devops_mcps.main_entry.register_tools")
  @patch("devops_mcps.main_entry.load_and_register_prompts")
  def test_setup_and_run_invalid_mount_path(
    self,
    mock_load_prompts,
    mock_register_tools,
    mock_initialize_clients,
    mock_create_server,
  ):
    """Test setup_and_run with invalid mount_path."""
    mock_server = MagicMock()
    mock_create_server.return_value = mock_server

    # Case 1: None
    main_entry.setup_and_run(transport="http", mount_path=None)
    mock_server.run.assert_called_with(transport="streamable-http", mount_path="/mcp")

    # Case 2: No leading slash
    main_entry.setup_and_run(transport="http", mount_path="mcp")
    mock_server.run.assert_called_with(transport="streamable-http", mount_path="/mcp")

  def test_main_stream_http_value_error(self):
    """Test main_stream_http handling of ValueError during index lookup."""
    # This is tricky because we need sys.argv to behave like a list but raise ValueError on index
    # even if 'in' returns True.

    class MockArgv(list):
      def __contains__(self, item):
        if item == "--transport":
          return True
        return super().__contains__(item)

      def index(self, item):
        if item == "--transport":
          raise ValueError("Mocked ValueError")
        return super().index(item)

    # Create mock argv with "--transport" "stdio" so it enters the logic
    mock_argv = MockArgv(["script.py", "--transport", "stdio"])

    with patch("sys.argv", mock_argv):
      with patch("devops_mcps.main_entry.main"):
        main_entry.main_stream_http()

        # Should have extended with stream_http
        self.assertEqual(mock_argv[-1], "stream_http")
        self.assertEqual(mock_argv[-2], "--transport")

  def test_run_as_script(self):
    """Test running the module as a script."""
    # Use subprocess to run the module
    # This covers the if __name__ == "__main__": block
    env = os.environ.copy()
    # Ensure we can import devops_mcps
    src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
    # We don't need PYTHONPATH if we change cwd to src, but keeping it is safe
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(
      [sys.executable, "-m", "devops_mcps.main_entry", "--version"],
      env=env,
      cwd=src_path,  # Change CWD to src to avoid picking up root devops_mcps
      capture_output=True,
      text=True,
    )

    # Check for failure details if return code is not 0
    if result.returncode != 0:
      print(f"Subprocess failed. Stdout: {result.stdout}")
      print(f"Subprocess failed. Stderr: {result.stderr}")

    self.assertEqual(
      result.returncode, 0, f"Subprocess failed with stderr: {result.stderr}"
    )
    # Check if version is printed (format: x.y.z)
    self.assertTrue(len(result.stdout.strip()) > 0)
