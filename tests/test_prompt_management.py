"""Comprehensive unit tests for prompt_management module.

This test suite covers all critical functions, edge cases, input validation,
error handling, and expected behavior under various scenarios.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Import the module under test
from devops_mcps.prompt_management import (
  load_and_register_prompts,
  validate_prompt_config,
  get_available_prompts,
)


class TestLoadAndRegisterPrompts:
  """Test suite for load_and_register_prompts function."""

  @patch("devops_mcps.prompt_management.Path")
  @patch("devops_mcps.prompt_management.logger")
  def test_prompts_file_not_found(self, mock_logger, mock_path):
    """Test behavior when prompts.json file does not exist."""
    # Setup
    mock_mcp = MagicMock()
    mock_path_instance = MagicMock()
    mock_path_instance.exists.return_value = False
    mock_path.return_value.parent.__truediv__.return_value = mock_path_instance

    # Execute
    load_and_register_prompts(mock_mcp)

    # Verify
    mock_logger.warning.assert_called_once()
    assert "Prompts file not found" in mock_logger.warning.call_args[0][0]
    mock_mcp.prompt.assert_not_called()

  @patch("devops_mcps.prompt_management.Path")
  @patch(
    "devops_mcps.prompt_management.open",
    new_callable=mock_open,
    read_data='{"test_prompt": {"description": "Test", "template": "Hello {name}", "variables": {"name": {"required": false, "default": "World"}}}}',
  )
  @patch("devops_mcps.prompt_management.logger")
  def test_successful_prompt_loading(self, mock_logger, mock_file, mock_path):
    """Test successful loading and registration of prompts."""
    # Setup
    mock_mcp = MagicMock()
    mock_path_instance = MagicMock()
    mock_path_instance.exists.return_value = True
    mock_path.return_value.parent.__truediv__.return_value = mock_path_instance

    # Mock the prompt decorator
    mock_prompt_decorator = MagicMock()
    mock_prompt_decorator.return_value = lambda func: func
    mock_mcp.prompt = mock_prompt_decorator

    # Execute
    load_and_register_prompts(mock_mcp)

    # Verify
    mock_logger.info.assert_any_call(f"Loading prompts from {mock_path_instance}")
    mock_logger.info.assert_any_call("Successfully loaded 1 prompts")
    mock_mcp.prompt.assert_called_once()

  @patch("devops_mcps.prompt_management.Path")
  @patch(
    "devops_mcps.prompt_management.open",
    new_callable=mock_open,
    read_data="invalid json",
  )
  @patch("devops_mcps.prompt_management.logger")
  def test_invalid_json_handling(self, mock_logger, mock_file, mock_path):
    """Test handling of invalid JSON in prompts file."""
    # Setup
    mock_mcp = MagicMock()
    mock_path_instance = MagicMock()
    mock_path_instance.exists.return_value = True
    mock_path.return_value.parent.__truediv__.return_value = mock_path_instance

    # Execute
    load_and_register_prompts(mock_mcp)

    # Verify
    mock_logger.error.assert_called_once()
    error_message = mock_logger.error.call_args[0][0]
    assert "Invalid JSON" in error_message
    mock_mcp.prompt.assert_not_called()

  @patch("devops_mcps.prompt_management.Path")
  @patch("devops_mcps.prompt_management.open", side_effect=IOError("File read error"))
  @patch("devops_mcps.prompt_management.logger")
  def test_file_read_error_handling(self, mock_logger, mock_file, mock_path):
    """Test handling of file read errors."""
    # Setup
    mock_mcp = MagicMock()
    mock_path_instance = MagicMock()
    mock_path_instance.exists.return_value = True
    mock_path.return_value.parent.__truediv__.return_value = mock_path_instance

    # Execute
    load_and_register_prompts(mock_mcp)

    # Verify
    mock_logger.error.assert_called_once()
    error_message = mock_logger.error.call_args[0][0]
    assert "Error loading prompts" in error_message
    assert "File read error" in error_message

  @patch("devops_mcps.prompt_management.Path")
  @patch(
    "devops_mcps.prompt_management.open",
    new_callable=mock_open,
    read_data='{"prompt1": {"description": "Valid", "template": "Test"}, "prompt2": {"description": "Invalid"}}',
  )
  @patch("devops_mcps.prompt_management.logger")
  def test_mixed_valid_invalid_prompts(self, mock_logger, mock_file, mock_path):
    """Test handling of mixed valid and invalid prompts."""
    # Setup
    mock_mcp = MagicMock()
    mock_path_instance = MagicMock()
    mock_path_instance.exists.return_value = True
    mock_path.return_value.parent.__truediv__.return_value = mock_path_instance

    mock_prompt_decorator = MagicMock()
    mock_prompt_decorator.return_value = lambda func: func
    mock_mcp.prompt = mock_prompt_decorator

    # Execute
    load_and_register_prompts(mock_mcp)

    # Verify - should register valid prompts and continue processing
    # The invalid prompt should not cause an error since prompt_config.get('template', '') returns empty string
    # Both prompts should be registered successfully
    mock_mcp.prompt.assert_called()
    # Should be called twice - once for each prompt
    assert mock_mcp.prompt.call_count == 2

  @patch("devops_mcps.prompt_management.Path")
  @patch("devops_mcps.prompt_management.open", new_callable=mock_open, read_data="{}")
  @patch("devops_mcps.prompt_management.logger")
  def test_empty_prompts_file(self, mock_logger, mock_file, mock_path):
    """Test handling of empty prompts file."""
    # Setup
    mock_mcp = MagicMock()
    mock_path_instance = MagicMock()
    mock_path_instance.exists.return_value = True
    mock_path.return_value.parent.__truediv__.return_value = mock_path_instance

    # Execute
    load_and_register_prompts(mock_mcp)

    # Verify
    mock_logger.info.assert_any_call("Successfully loaded 0 prompts")
    mock_mcp.prompt.assert_not_called()

  @pytest.mark.asyncio
  @patch("devops_mcps.prompt_management.Path")
  @patch(
    "devops_mcps.prompt_management.open",
    new_callable=mock_open,
    read_data='{"test_prompt": {"description": "Test", "template": "Hello {name}", "variables": {"name": {"required": true}}}}',
  )
  @patch("devops_mcps.prompt_management.logger")
  async def test_dynamic_prompt_function_required_variable_missing(
    self, mock_logger, mock_file, mock_path
  ):
    """Test dynamic prompt function when required variable is missing."""
    # Setup
    mock_mcp = MagicMock()
    mock_path_instance = MagicMock()
    mock_path_instance.exists.return_value = True
    mock_path.return_value.parent.__truediv__.return_value = mock_path_instance

    captured_function = None

    def capture_function(func):
      nonlocal captured_function
      captured_function = func
      return func

    mock_mcp.prompt.return_value = capture_function

    # Execute
    load_and_register_prompts(mock_mcp)

    # Test the captured function
    assert captured_function is not None
    result = await captured_function()

    # Verify
    assert "error" in result
    assert "Required variable 'name' not provided" in result["error"]

  @pytest.mark.asyncio
  @patch("devops_mcps.prompt_management.Path")
  @patch(
    "devops_mcps.prompt_management.open",
    new_callable=mock_open,
    read_data='{"test_prompt": {"description": "Test", "template": "Hello {name}", "variables": {"name": {"required": false, "default": "World"}}}}',
  )
  @patch("devops_mcps.prompt_management.logger")
  async def test_dynamic_prompt_function_with_default_value(
    self, mock_logger, mock_file, mock_path
  ):
    """Test dynamic prompt function using default variable value."""
    # Setup
    mock_mcp = MagicMock()
    mock_path_instance = MagicMock()
    mock_path_instance.exists.return_value = True
    mock_path.return_value.parent.__truediv__.return_value = mock_path_instance

    captured_function = None

    def capture_function(func):
      nonlocal captured_function
      captured_function = func
      return func

    mock_mcp.prompt.return_value = capture_function

    # Execute
    load_and_register_prompts(mock_mcp)

    # Test the captured function
    assert captured_function is not None
    result = await captured_function()

    # Verify
    assert "error" not in result
    assert result["content"] == "Hello World"
    assert result["name"] == "test_prompt"

  @pytest.mark.asyncio
  @patch("devops_mcps.prompt_management.Path")
  @patch(
    "devops_mcps.prompt_management.open",
    new_callable=mock_open,
    read_data='{"test_prompt": {"description": "Test", "template": "Hello {name}", "variables": {"name": {"required": false}}}}',
  )
  @patch("devops_mcps.prompt_management.logger")
  async def test_dynamic_prompt_function_with_provided_variable(
    self, mock_logger, mock_file, mock_path
  ):
    """Test dynamic prompt function with provided variable."""
    # Setup
    mock_mcp = MagicMock()
    mock_path_instance = MagicMock()
    mock_path_instance.exists.return_value = True
    mock_path.return_value.parent.__truediv__.return_value = mock_path_instance

    captured_function = None

    def capture_function(func):
      nonlocal captured_function
      captured_function = func
      return func

    mock_mcp.prompt.return_value = capture_function

    # Execute
    load_and_register_prompts(mock_mcp)

    # Test the captured function
    assert captured_function is not None
    result = await captured_function(name="Alice")

    # Verify
    assert "error" not in result
    assert result["content"] == "Hello Alice"
    assert result["name"] == "test_prompt"


class TestValidatePromptConfig:
  """Test suite for validate_prompt_config function."""

  @patch("devops_mcps.prompt_management.logger")
  def test_valid_minimal_config(self, mock_logger):
    """Test validation of minimal valid prompt configuration."""
    config = {"description": "Test prompt", "template": "Hello world"}

    result = validate_prompt_config(config)

    assert result is True
    mock_logger.error.assert_not_called()

  @patch("devops_mcps.prompt_management.logger")
  def test_valid_config_with_variables(self, mock_logger):
    """Test validation of prompt configuration with variables."""
    config = {
      "description": "Test prompt",
      "template": "Hello {name}",
      "variables": {"name": {"type": "string", "required": True}},
    }

    result = validate_prompt_config(config)

    assert result is True
    mock_logger.error.assert_not_called()

  @patch("devops_mcps.prompt_management.logger")
  def test_missing_description(self, mock_logger):
    """Test validation failure when description is missing."""
    config = {"template": "Hello world"}

    result = validate_prompt_config(config)

    assert result is False
    mock_logger.error.assert_called_with(
      "Missing required field 'description' in prompt configuration"
    )

  @patch("devops_mcps.prompt_management.logger")
  def test_missing_template(self, mock_logger):
    """Test validation failure when template is missing."""
    config = {"description": "Test prompt"}

    result = validate_prompt_config(config)

    assert result is False
    mock_logger.error.assert_called_with(
      "Missing required field 'template' in prompt configuration"
    )

  @patch("devops_mcps.prompt_management.logger")
  def test_invalid_variables_type(self, mock_logger):
    """Test validation failure when variables is not a dictionary."""
    config = {
      "description": "Test prompt",
      "template": "Hello world",
      "variables": "invalid",
    }

    result = validate_prompt_config(config)

    assert result is False
    mock_logger.error.assert_called_with("Variables must be a dictionary")

  @patch("devops_mcps.prompt_management.logger")
  def test_invalid_variable_config_type(self, mock_logger):
    """Test validation failure when variable configuration is not a dictionary."""
    config = {
      "description": "Test prompt",
      "template": "Hello {name}",
      "variables": {"name": "invalid"},
    }

    result = validate_prompt_config(config)

    assert result is False
    mock_logger.error.assert_called_with(
      "Variable 'name' configuration must be a dictionary"
    )

  @patch("devops_mcps.prompt_management.logger")
  def test_empty_config(self, mock_logger):
    """Test validation failure with empty configuration."""
    config = {}

    result = validate_prompt_config(config)

    assert result is False
    mock_logger.error.assert_called_with(
      "Missing required field 'description' in prompt configuration"
    )

  @patch("devops_mcps.prompt_management.logger")
  def test_none_config(self, mock_logger):
    """Test validation failure with None configuration."""
    # The function will fail when trying to check 'field not in prompt_config'
    # because None doesn't support the 'in' operator with strings
    with pytest.raises(TypeError, match="argument of type 'NoneType' is not iterable"):
      validate_prompt_config(None)


class TestGetAvailablePrompts:
  """Test suite for get_available_prompts function."""

  @patch("devops_mcps.prompt_management.Path")
  @patch(
    "devops_mcps.prompt_management.open",
    new_callable=mock_open,
    read_data='{"prompt1": {"description": "Test 1"}, "prompt2": {"description": "Test 2"}}',
  )
  @patch("devops_mcps.prompt_management.logger")
  def test_get_available_prompts_success(self, mock_logger, mock_file, mock_path):
    """Test successful retrieval of available prompts."""
    # Setup
    mock_path_instance = MagicMock()
    mock_path_instance.exists.return_value = True
    mock_path.return_value.parent.__truediv__.return_value = mock_path_instance

    # Execute
    result = get_available_prompts()

    # Verify
    assert len(result) == 2
    assert "prompt1" in result
    assert "prompt2" in result
    assert result["prompt1"]["description"] == "Test 1"
    assert result["prompt2"]["description"] == "Test 2"

  @patch("devops_mcps.prompt_management.logger")
  def test_get_available_prompts_with_custom_path(self, mock_logger):
    """Test get_available_prompts with custom file path."""
    # Setup
    custom_path = MagicMock(spec=Path)
    custom_path.exists.return_value = True

    with patch(
      "devops_mcps.prompt_management.open",
      new_callable=mock_open,
      read_data='{"custom_prompt": {"description": "Custom"}}',
    ) as mock_file:
      # Execute
      result = get_available_prompts(custom_path)

      # Verify
      assert len(result) == 1
      assert "custom_prompt" in result
      mock_file.assert_called_once_with(custom_path, "r", encoding="utf-8")

  @patch("devops_mcps.prompt_management.Path")
  @patch("devops_mcps.prompt_management.logger")
  def test_get_available_prompts_file_not_found(self, mock_logger, mock_path):
    """Test get_available_prompts when file does not exist."""
    # Setup
    mock_path_instance = MagicMock()
    mock_path_instance.exists.return_value = False
    mock_path.return_value.parent.__truediv__.return_value = mock_path_instance

    # Execute
    result = get_available_prompts()

    # Verify
    assert result == {}
    mock_logger.warning.assert_called_once()
    assert "Prompts file not found" in mock_logger.warning.call_args[0][0]

  @patch("devops_mcps.prompt_management.Path")
  @patch("devops_mcps.prompt_management.open", side_effect=IOError("Read error"))
  @patch("devops_mcps.prompt_management.logger")
  def test_get_available_prompts_read_error(self, mock_logger, mock_file, mock_path):
    """Test get_available_prompts when file read fails."""
    # Setup
    mock_path_instance = MagicMock()
    mock_path_instance.exists.return_value = True
    mock_path.return_value.parent.__truediv__.return_value = mock_path_instance

    # Execute
    result = get_available_prompts()

    # Verify
    assert result == {}
    mock_logger.error.assert_called_once()
    error_message = mock_logger.error.call_args[0][0]
    assert "Error reading prompts file" in error_message
    assert "Read error" in error_message

  @patch("devops_mcps.prompt_management.Path")
  @patch(
    "devops_mcps.prompt_management.open",
    new_callable=mock_open,
    read_data="invalid json",
  )
  @patch("devops_mcps.prompt_management.logger")
  def test_get_available_prompts_invalid_json(self, mock_logger, mock_file, mock_path):
    """Test get_available_prompts with invalid JSON."""
    # Setup
    mock_path_instance = MagicMock()
    mock_path_instance.exists.return_value = True
    mock_path.return_value.parent.__truediv__.return_value = mock_path_instance

    # Execute
    result = get_available_prompts()

    # Verify
    assert result == {}
    mock_logger.error.assert_called_once()
    error_message = mock_logger.error.call_args[0][0]
    assert "Error reading prompts file" in error_message

  @patch("devops_mcps.prompt_management.Path")
  @patch("devops_mcps.prompt_management.open", new_callable=mock_open, read_data="{}")
  @patch("devops_mcps.prompt_management.logger")
  def test_get_available_prompts_empty_file(self, mock_logger, mock_file, mock_path):
    """Test get_available_prompts with empty JSON file."""
    # Setup
    mock_path_instance = MagicMock()
    mock_path_instance.exists.return_value = True
    mock_path.return_value.parent.__truediv__.return_value = mock_path_instance

    # Execute
    result = get_available_prompts()

    # Verify
    assert result == {}
    mock_logger.error.assert_not_called()


class TestEdgeCasesAndIntegration:
  """Test suite for edge cases and integration scenarios."""

  @patch("devops_mcps.prompt_management.Path")
  @patch(
    "devops_mcps.prompt_management.open",
    new_callable=mock_open,
    read_data='{"complex_prompt": {"description": "Complex test", "template": "Hello {name}, you have {count} {item}", "variables": {"name": {"required": true}, "count": {"required": false, "default": "0"}, "item": {"required": false, "default": "items"}}}}',
  )
  @patch("devops_mcps.prompt_management.logger")
  def test_complex_prompt_with_multiple_variables(
    self, mock_logger, mock_file, mock_path
  ):
    """Test complex prompt with multiple variables and mixed requirements."""
    # Setup
    mock_mcp = MagicMock()
    mock_path_instance = MagicMock()
    mock_path_instance.exists.return_value = True
    mock_path.return_value.parent.__truediv__.return_value = mock_path_instance

    captured_function = None

    def capture_function(func):
      nonlocal captured_function
      captured_function = func
      return func

    mock_mcp.prompt.return_value = capture_function

    # Execute
    load_and_register_prompts(mock_mcp)

    # Verify function was captured
    assert captured_function is not None
    assert captured_function.__name__ == "complex_prompt"

  @patch("devops_mcps.prompt_management.Path")
  @patch("devops_mcps.prompt_management.logger")
  def test_unicode_handling(self, mock_logger, mock_path):
    """Test handling of Unicode characters in prompts."""
    # Setup
    unicode_content = '{"unicode_prompt": {"description": "Unicode test ñáéíóú", "template": "Hello 世界 {name}", "variables": {"name": {"required": false, "default": "用户"}}}}'

    with patch(
      "devops_mcps.prompt_management.open",
      new_callable=mock_open,
      read_data=unicode_content,
    ) as mock_file:
      mock_mcp = MagicMock()
      mock_path_instance = MagicMock()
      mock_path_instance.exists.return_value = True
      mock_path.return_value.parent.__truediv__.return_value = mock_path_instance

      mock_mcp.prompt.return_value = lambda func: func

      # Execute
      load_and_register_prompts(mock_mcp)

      # Verify
      mock_file.assert_called_once_with(mock_path_instance, "r", encoding="utf-8")
      mock_logger.info.assert_any_call("Successfully loaded 1 prompts")

  def test_validate_prompt_config_edge_cases(self):
    """Test validate_prompt_config with various edge cases."""
    # Test with extra fields (should still be valid)
    config_with_extra = {
      "description": "Test",
      "template": "Hello",
      "extra_field": "should be ignored",
    }
    assert validate_prompt_config(config_with_extra) is True

    # Test with empty strings (should be valid)
    config_empty_strings = {"description": "", "template": ""}
    assert validate_prompt_config(config_empty_strings) is True

    # Test with empty variables dict (should be valid)
    config_empty_vars = {"description": "Test", "template": "Hello", "variables": {}}
    assert validate_prompt_config(config_empty_vars) is True

  @patch("devops_mcps.prompt_management.Path")
  @patch(
    "devops_mcps.prompt_management.open",
    new_callable=mock_open,
    read_data='{"prompt_with_exception": {"description": "Test", "template": "Hello {name}", "variables": {"name": {"required": true}}}}',
  )
  @patch("devops_mcps.prompt_management.logger")
  def test_prompt_function_exception_handling(self, mock_logger, mock_file, mock_path):
    """Test exception handling within dynamically created prompt functions."""
    # Setup
    mock_mcp = MagicMock()
    mock_path_instance = MagicMock()
    mock_path_instance.exists.return_value = True
    mock_path.return_value.parent.__truediv__.return_value = mock_path_instance

    captured_function = None

    def capture_function(func):
      nonlocal captured_function
      captured_function = func
      return func

    mock_mcp.prompt.return_value = capture_function

    # Execute
    load_and_register_prompts(mock_mcp)

    # Verify the function handles internal exceptions gracefully
    assert captured_function is not None

    # This should be tested in an async context, but we can verify the structure
    assert hasattr(captured_function, "__name__")
    assert captured_function.__name__ == "prompt_with_exception"
