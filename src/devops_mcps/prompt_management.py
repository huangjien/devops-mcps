"""Prompt management module for loading and registering dynamic prompts.

This module handles the loading of prompts from JSON files and their
registration with the FastMCP server instance.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional


# Get logger for this module
logger = logging.getLogger(__name__)


def load_and_register_prompts(mcp) -> None:
  """Load and register dynamic prompts from JSON file.

  Args:
      mcp: FastMCP server instance to register prompts with
  """
  # Get the directory where this module is located
  current_dir = Path(__file__).parent
  prompts_file = current_dir / "prompts.json"

  if not prompts_file.exists():
    logger.warning(f"Prompts file not found: {prompts_file}")
    return

  try:
    with open(prompts_file, "r", encoding="utf-8") as f:
      prompts_data = json.load(f)

    logger.info(f"Loading prompts from {prompts_file}")

    for prompt_name, prompt_config in prompts_data.items():
      try:
        # Create a simple data container for this prompt
        class PromptData:
          def __init__(self, name, description, template, variables):
            self.name = name
            self.description = description
            self.template = template
            self.variables = variables

        prompt_data = PromptData(
          name=prompt_name,
          description=prompt_config.get("description", ""),
          template=prompt_config.get("template", ""),
          variables=prompt_config.get("variables", {}),
        )

        # Register the prompt with the MCP server
        @mcp.prompt()
        async def dynamic_prompt(data=prompt_data, **kwargs) -> Dict[str, Any]:
          """Dynamically generated prompt function."""
          try:
            # Process template variables
            processed_template = data.template

            # Handle conditional blocks (if any)
            # This is a simplified implementation - you might want to extend this
            # based on your specific conditional logic requirements

            # Replace variables in the template
            for var_name, var_config in data.variables.items():
              if var_name in kwargs:
                value = kwargs[var_name]
                processed_template = processed_template.replace(
                  f"{{{var_name}}}", str(value)
                )
              elif var_config.get("required", False):
                return {"error": f"Required variable '{var_name}' not provided"}
              else:
                # Use default value if available
                default_value = var_config.get("default", "")
                processed_template = processed_template.replace(
                  f"{{{var_name}}}", str(default_value)
                )

            return {
              "name": data.name,
              "description": data.description,
              "content": processed_template,
              "variables": data.variables,
            }

          except Exception as e:
            logger.error(f"Error processing prompt '{data.name}': {e}")
            return {"error": f"Error processing prompt: {e}"}

        # Set the function name dynamically
        dynamic_prompt.__name__ = prompt_name
        dynamic_prompt.__doc__ = prompt_config.get("description", "")

        logger.debug(f"Registered prompt: {prompt_name}")

      except Exception as e:
        logger.error(f"Failed to register prompt '{prompt_name}': {e}")
        continue

    logger.info(f"Successfully loaded {len(prompts_data)} prompts")

  except json.JSONDecodeError as e:
    logger.error(f"Invalid JSON in prompts file {prompts_file}: {e}")
  except Exception as e:
    logger.error(f"Error loading prompts from {prompts_file}: {e}")


def validate_prompt_config(prompt_config: Dict[str, Any]) -> bool:
  """Validate a prompt configuration dictionary.

  Args:
      prompt_config: Dictionary containing prompt configuration

  Returns:
      bool: True if configuration is valid, False otherwise
  """
  required_fields = ["description", "template"]

  for field in required_fields:
    if field not in prompt_config:
      logger.error(f"Missing required field '{field}' in prompt configuration")
      return False

  # Validate variables if present
  if "variables" in prompt_config:
    variables = prompt_config["variables"]
    if not isinstance(variables, dict):
      logger.error("Variables must be a dictionary")
      return False

    for var_name, var_config in variables.items():
      if not isinstance(var_config, dict):
        logger.error(f"Variable '{var_name}' configuration must be a dictionary")
        return False

  return True


def get_available_prompts(
  prompts_file: Optional[Path] = None,
) -> Dict[str, Dict[str, Any]]:
  """Get a dictionary of available prompts from the prompts file.

  Args:
      prompts_file: Optional path to prompts file. If None, uses default location.

  Returns:
      Dict containing available prompts and their configurations
  """
  if prompts_file is None:
    current_dir = Path(__file__).parent
    prompts_file = current_dir / "prompts.json"

  if not prompts_file.exists():
    logger.warning(f"Prompts file not found: {prompts_file}")
    return {}

  try:
    with open(prompts_file, "r", encoding="utf-8") as f:
      return json.load(f)
  except Exception as e:
    logger.error(f"Error reading prompts file {prompts_file}: {e}")
    return {}
