"""Prompt management module for loading and registering dynamic prompts.

This module handles the loading of prompts from JSON files and their
registration with the FastMCP server instance.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


# Get logger for this module
logger = logging.getLogger(__name__)


def _resolve_prompts_file(prompts_file: Optional[Path] = None) -> Tuple[Path, bool]:
  if prompts_file is not None:
    return prompts_file, True

  env_path = os.getenv("PROMPTS_FILE")
  if env_path:
    return Path(env_path), True

  current_dir = Path(__file__).parent
  return current_dir / "prompts.json", False


def _iter_prompt_entries(prompts_data: Any) -> Iterable[Tuple[str, Dict[str, Any]]]:
  if isinstance(prompts_data, dict) and "prompts" in prompts_data:
    prompts_list = prompts_data.get("prompts", [])
    if isinstance(prompts_list, list):
      for prompt in prompts_list:
        if isinstance(prompt, dict) and "name" in prompt:
          yield str(prompt["name"]), prompt
      return

  if isinstance(prompts_data, list):
    for prompt in prompts_data:
      if isinstance(prompt, dict) and "name" in prompt:
        yield str(prompt["name"]), prompt
    return

  if isinstance(prompts_data, dict):
    for prompt_name, prompt_config in prompts_data.items():
      if isinstance(prompt_config, dict):
        yield str(prompt_name), prompt_config


def _build_variable_specs(prompt_config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
  variables = prompt_config.get("variables")
  if isinstance(variables, dict):
    return variables

  arguments = prompt_config.get("arguments")
  if isinstance(arguments, list):
    specs: Dict[str, Dict[str, Any]] = {}
    for arg in arguments:
      if not isinstance(arg, dict):
        continue
      name = arg.get("name")
      if not name:
        continue
      specs[str(name)] = {
        "required": bool(arg.get("required", False)),
        "default": arg.get("default", ""),
      }
    return specs

  return {}


def _render_template(
  template: str, variable_specs: Dict[str, Dict[str, Any]], kwargs: Dict[str, Any]
) -> Tuple[Optional[str], Optional[str]]:
  for var_name, var_spec in variable_specs.items():
    if var_spec.get("required", False) and var_name not in kwargs:
      return None, f"Required variable '{var_name}' not provided"

  rendered = template

  for var_name in variable_specs.keys():
    section_pattern = re.compile(
      r"{{#\s*"
      + re.escape(var_name)
      + r"\s*}}([\s\S]*?){{/\s*"
      + re.escape(var_name)
      + r"\s*}}"
    )
    if kwargs.get(var_name):
      rendered = section_pattern.sub(r"\1", rendered)
    else:
      rendered = section_pattern.sub("", rendered)

  for var_name, var_spec in variable_specs.items():
    if var_name in kwargs:
      value = kwargs[var_name]
    else:
      value = var_spec.get("default", "")

    rendered = rendered.replace(f"{{{var_name}}}", str(value))
    rendered = re.sub(r"{{\s*" + re.escape(var_name) + r"\s*}}", str(value), rendered)

  rendered = re.sub(r"{{#\s*[^}]+\s*}}[\s\S]*?{{/\s*[^}]+\s*}}", "", rendered)
  return rendered, None


def _as_prompt_messages(text: str) -> List[Dict[str, Any]]:
  return [{"role": "user", "content": [{"type": "text", "text": text}]}]


def _make_dynamic_prompt(
  *,
  prompt_name: str,
  description: str,
  template: str,
  variable_specs: Dict[str, Dict[str, Any]],
):
  async def dynamic_prompt(**kwargs) -> List[Dict[str, Any]]:
    try:
      processed_template, error = _render_template(
        template=template,
        variable_specs=variable_specs,
        kwargs=kwargs,
      )
      if error:
        return _as_prompt_messages(error)

      return _as_prompt_messages(processed_template or "")
    except Exception as e:
      logger.error(f"Error processing prompt '{prompt_name}': {e}")
      return _as_prompt_messages(f"Error processing prompt: {e}")

  dynamic_prompt.__name__ = prompt_name
  dynamic_prompt.__doc__ = str(description)
  return dynamic_prompt


def load_and_register_prompts(mcp, prompts_file: Optional[Path] = None) -> None:
  """Load and register dynamic prompts from JSON file.

  Args:
      mcp: FastMCP server instance to register prompts with
      prompts_file: Optional explicit path to prompts JSON
  """
  prompts_file, configured = _resolve_prompts_file(prompts_file)

  if not prompts_file.exists():
    if configured:
      logger.warning(f"Prompts file not found: {prompts_file}")
    return

  try:
    with open(prompts_file, "r", encoding="utf-8") as f:
      prompts_data = json.load(f)

    logger.info(f"Loading prompts from {prompts_file}")

    prompt_entries = list(_iter_prompt_entries(prompts_data))
    for prompt_name, prompt_config in prompt_entries:
      try:
        description = prompt_config.get("description", "")
        template = prompt_config.get("template", "")
        variable_specs = _build_variable_specs(prompt_config)

        dynamic_prompt = _make_dynamic_prompt(
          prompt_name=str(prompt_name),
          description=str(description),
          template=str(template),
          variable_specs=variable_specs,
        )

        mcp.prompt(name=prompt_name, description=str(description))(dynamic_prompt)
        logger.debug(f"Registered prompt: {prompt_name}")

      except Exception as e:
        logger.error(f"Failed to register prompt '{prompt_name}': {e}")
        continue

    logger.info(f"Successfully loaded {len(prompt_entries)} prompts")

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
  prompts_file, configured = _resolve_prompts_file(prompts_file)

  if not prompts_file.exists():
    if configured:
      logger.warning(f"Prompts file not found: {prompts_file}")
    return {}

  try:
    with open(prompts_file, "r", encoding="utf-8") as f:
      return json.load(f)
  except Exception as e:
    logger.error(f"Error reading prompts file {prompts_file}: {e}")
    return {}
