import json
import os
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class PromptLoader:
  """Loads and manages dynamic prompts from JSON files."""

  def __init__(self, prompts_file: Optional[str] = None):
    """
    Initialize the PromptLoader.

    Args:
        prompts_file: Path to the prompts JSON file. If None, uses PROMPTS_FILE env var.
    """
    self.prompts_file = prompts_file or os.getenv("PROMPTS_FILE")
    self.prompts = {}

  def load_prompts(self) -> Dict[str, Any]:
    """
    Load prompts from the JSON file.

    Returns:
        Dictionary of loaded prompts.
    """
    if not self.prompts_file:
      logger.warning("No prompts file specified")
      return {}

    if not os.path.exists(self.prompts_file):
      logger.warning(f"Prompts file not found: {self.prompts_file}")
      return {}

    try:
      with open(self.prompts_file, "r", encoding="utf-8") as f:
        data = json.load(f)

      if not isinstance(data, dict) or "prompts" not in data:
        logger.error("Invalid prompts file format. Expected JSON with 'prompts' key.")
        return {}

      prompts_list = data["prompts"]
      if not isinstance(prompts_list, list):
        logger.error("Invalid prompts format. Expected 'prompts' to be a list.")
        return {}

      loaded_prompts = {}
      for prompt in prompts_list:
        if self._validate_prompt(prompt):
          loaded_prompts[prompt["name"]] = prompt
        else:
          logger.warning(f"Skipping invalid prompt: {prompt.get('name', 'unknown')}")

      self.prompts = loaded_prompts
      logger.info(f"Loaded {len(loaded_prompts)} prompts from {self.prompts_file}")
      return loaded_prompts

    except json.JSONDecodeError as e:
      logger.error(f"Failed to parse prompts file {self.prompts_file}: {e}")
      return {}
    except Exception as e:
      logger.error(f"Error loading prompts from {self.prompts_file}: {e}")
      return {}

  def _validate_prompt(self, prompt: Dict[str, Any]) -> bool:
    """
    Validate a prompt structure.

    Args:
        prompt: Prompt dictionary to validate.

    Returns:
        True if valid, False otherwise.
    """
    required_fields = ["name", "description", "template"]
    for field in required_fields:
      if field not in prompt:
        logger.error(f"Prompt missing required field: {field}")
        return False

    if "arguments" in prompt:
      if not isinstance(prompt["arguments"], list):
        logger.error(f"Prompt {prompt['name']}: arguments must be a list")
        return False

      for arg in prompt["arguments"]:
        if not isinstance(arg, dict) or "name" not in arg:
          logger.error(f"Prompt {prompt['name']}: invalid argument structure")
          return False

    return True

  def get_prompt(self, name: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific prompt by name.

    Args:
        name: Name of the prompt.

    Returns:
        Prompt dictionary or None if not found.
    """
    return self.prompts.get(name)

  def list_prompts(self) -> List[str]:
    """
    Get a list of all prompt names.

    Returns:
        List of prompt names.
    """
    return list(self.prompts.keys())
