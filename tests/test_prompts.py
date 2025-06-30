import json
import os
import tempfile
from unittest.mock import patch

from src.devops_mcps.prompts import PromptLoader


class TestPromptLoader:
  """Test cases for PromptLoader class."""

  def test_init_with_file_path(self):
    """Test initialization with explicit file path."""
    loader = PromptLoader("/path/to/prompts.json")
    assert loader.prompts_file == "/path/to/prompts.json"
    assert loader.prompts == {}

  @patch.dict(os.environ, {"PROMPTS_FILE": "/env/prompts.json"})
  def test_init_with_env_var(self):
    """Test initialization with environment variable."""
    loader = PromptLoader()
    assert loader.prompts_file == "/env/prompts.json"

  def test_init_no_file(self):
    """Test initialization without file path or env var."""
    with patch.dict(os.environ, {}, clear=True):
      loader = PromptLoader()
      assert loader.prompts_file is None

  def test_load_prompts_no_file_specified(self):
    """Test loading prompts when no file is specified."""
    with patch.dict(os.environ, {}, clear=True):
      loader = PromptLoader()
      result = loader.load_prompts()
      assert result == {}

  def test_load_prompts_file_not_found(self):
    """Test loading prompts when file doesn't exist."""
    loader = PromptLoader("/nonexistent/file.json")
    result = loader.load_prompts()
    assert result == {}

  def test_load_prompts_invalid_json(self):
    """Test loading prompts with invalid JSON."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
      f.write("invalid json content")
      f.flush()

      try:
        loader = PromptLoader(f.name)
        result = loader.load_prompts()
        assert result == {}
      finally:
        os.unlink(f.name)

  def test_load_prompts_missing_prompts_key(self):
    """Test loading prompts with missing 'prompts' key."""
    data = {"other_key": "value"}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
      json.dump(data, f)
      f.flush()

      try:
        loader = PromptLoader(f.name)
        result = loader.load_prompts()
        assert result == {}
      finally:
        os.unlink(f.name)

  def test_load_prompts_prompts_not_list(self):
    """Test loading prompts when 'prompts' is not a list."""
    data = {"prompts": "not a list"}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
      json.dump(data, f)
      f.flush()

      try:
        loader = PromptLoader(f.name)
        result = loader.load_prompts()
        assert result == {}
      finally:
        os.unlink(f.name)

  def test_load_prompts_valid_data(self):
    """Test loading valid prompts data."""
    data = {
      "prompts": [
        {
          "name": "test_prompt",
          "description": "A test prompt",
          "template": "This is a test prompt with {{variable}}",
          "arguments": [
            {"name": "variable", "description": "A test variable", "required": True}
          ],
        }
      ]
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
      json.dump(data, f)
      f.flush()

      try:
        loader = PromptLoader(f.name)
        result = loader.load_prompts()

        assert len(result) == 1
        assert "test_prompt" in result
        assert result["test_prompt"]["name"] == "test_prompt"
        assert result["test_prompt"]["description"] == "A test prompt"
        assert "{{variable}}" in result["test_prompt"]["template"]
        assert len(result["test_prompt"]["arguments"]) == 1
      finally:
        os.unlink(f.name)

  def test_validate_prompt_missing_required_fields(self):
    """Test prompt validation with missing required fields."""
    loader = PromptLoader()

    # Missing name
    prompt = {"description": "test", "template": "test"}
    assert not loader._validate_prompt(prompt)

    # Missing description
    prompt = {"name": "test", "template": "test"}
    assert not loader._validate_prompt(prompt)

    # Missing content
    prompt = {"name": "test", "description": "test"}
    assert not loader._validate_prompt(prompt)

  def test_validate_prompt_invalid_arguments(self):
    """Test prompt validation with invalid arguments."""
    loader = PromptLoader()

    # Arguments not a list
    prompt = {
      "name": "test",
      "description": "test",
      "template": "test",
      "arguments": "not a list",
    }
    assert not loader._validate_prompt(prompt)

    # Invalid argument structure
    prompt = {
      "name": "test",
      "description": "test",
      "template": "test",
      "arguments": [{"description": "missing name"}],
    }
    assert not loader._validate_prompt(prompt)

  def test_validate_prompt_valid(self):
    """Test prompt validation with valid prompt."""
    loader = PromptLoader()

    prompt = {
      "name": "test",
      "description": "test",
      "template": "test",
      "arguments": [{"name": "arg1", "description": "test arg"}],
    }
    assert loader._validate_prompt(prompt)

  def test_get_prompt(self):
    """Test getting a specific prompt."""
    loader = PromptLoader()
    loader.prompts = {"test_prompt": {"name": "test_prompt", "description": "test"}}

    result = loader.get_prompt("test_prompt")
    assert result is not None
    assert result["name"] == "test_prompt"

    result = loader.get_prompt("nonexistent")
    assert result is None

  def test_list_prompts(self):
    """Test listing all prompt names."""
    loader = PromptLoader()
    loader.prompts = {"prompt1": {"name": "prompt1"}, "prompt2": {"name": "prompt2"}}

    result = loader.list_prompts()
    assert len(result) == 2
    assert "prompt1" in result
    assert "prompt2" in result

  def test_load_prompts_skip_invalid(self):
    """Test that invalid prompts are skipped during loading."""
    data = {
      "prompts": [
        {
          "name": "valid_prompt",
          "description": "A valid prompt",
          "template": "Valid content",
        },
        {
          "name": "invalid_prompt",
          "description": "Missing content field",
          # Missing 'content' field
        },
      ]
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
      json.dump(data, f)
      f.flush()

      try:
        loader = PromptLoader(f.name)
        result = loader.load_prompts()

        # Only the valid prompt should be loaded
        assert len(result) == 1
        assert "valid_prompt" in result
        assert "invalid_prompt" not in result
      finally:
        os.unlink(f.name)
