"""Jenkins object conversion utilities."""

import logging
from typing import Any

# Third-party imports
from jenkinsapi.job import Job
from jenkinsapi.view import View

logger = logging.getLogger(__name__)


def _to_dict(obj: Any) -> Any:
  """Converts common Jenkins objects to dictionaries. Handles basic types and lists."""
  if isinstance(obj, (str, int, float, bool, type(None))):
    return obj
  if isinstance(obj, list):
    return [_to_dict(item) for item in obj]
  if isinstance(obj, dict):
    return {k: _to_dict(v) for k, v in obj.items()}

  if isinstance(obj, Job):
    return {
      "name": obj.name,
      "url": obj.baseurl,
      "is_enabled": obj.is_enabled(),
      "is_queued": obj.is_queued(),
      "in_queue": obj.is_queued(),  # corrected typo: in_queue
      "last_build_number": obj.get_last_buildnumber(),
      "last_build_url": obj.get_last_buildurl(),
    }
  if isinstance(obj, View):
    return {"name": obj.name, "url": obj.baseurl, "description": obj.get_description()}

  # Fallback
  try:
    logger.warning(
      f"No specific _to_dict handler for type {type(obj).__name__}, returning string representation."
    )
    return str(obj)
  except Exception as fallback_err:  # Catch potential errors during fallback
    logger.error(
      f"Error during fallback _to_dict for {type(obj).__name__}: {fallback_err}"
    )
    return f"<Error serializing object of type {type(obj).__name__}>"
