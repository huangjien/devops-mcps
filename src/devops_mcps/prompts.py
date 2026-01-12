# /Users/huangjien/workspace/devops-mcps/src/devops_mcps/prompts.py
"""Prompt management module for loading and managing dynamic prompts.

This module provides a unified interface for prompt loading and registration.
All functionality has been consolidated into prompt_management.py to avoid duplication.
This file is maintained for backward compatibility.

Note: This module now re-exports functionality from prompt_management.py
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

# Re-export from prompt_management module
from .prompt_management import (
  load_and_register_prompts,
  validate_prompt_config,
  get_available_prompts,
)

logger = logging.getLogger(__name__)


class PromptLoader:
  """Loads and manages dynamic prompts from JSON files.

  This class provides backward compatibility for code that uses the old
  PromptLoader interface. It now delegates to the consolidated prompt_management module.

  Note: This class expects the old JSON format with a "prompts" key.
        For new prompt format, use prompt_management.load_and_register_prompts() directly.
  """

  def __init__(self, prompts_file: Optional[str] = None):
    """
    Initialize PromptLoader.

    Args:
        prompts_file: Path to prompts JSON file. If None, uses PROMPTS_FILE env var.
    """
    import os

    self.prompts_file = prompts_file or os.getenv("PROMPTS_FILE")
    self.prompts = {}

  def load_prompts(self) -> Dict[str, Any]:
    """
    Load prompts from JSON file.

    Returns:
        Dictionary of loaded prompts.

    Note: This method supports the old format with "prompts" key.
          For new format, use prompt_management.get_available_prompts() instead.
    """
    import json

    if not self.prompts_file:
      logger.warning("No prompts file specified")
      return {}

    if not Path(self.prompts_file).exists():
      logger.warning(f"Prompts file not found: {self.prompts_file}")
      return {}

    try:
      with open(self.prompts_file, "r", encoding="utf-8") as f:
        data = json.load(f)

      # Support old format with "prompts" key
      if isinstance(data, dict) and "prompts" in data:
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
      # Support new format (dict of prompts)
      # Only return data if it appears to be a valid prompts dict (has prompts key or looks like prompts)
      elif isinstance(data, dict):
        self.prompts = data
        logger.info(f"Loaded {len(data)} prompts from {self.prompts_file}")
        return data
      else:
        logger.error("Invalid prompts file format.")
        return {}

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


# Re-export for backward compatibility
__all__ = [
  "PromptLoader",
  "load_and_register_prompts",
  "validate_prompt_config",
  "get_available_prompts",
]
