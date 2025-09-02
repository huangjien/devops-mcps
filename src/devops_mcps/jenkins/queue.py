"""
Jenkins queue management module.
Handles operations related to Jenkins build queue.
"""

from typing import Any, Dict, List, Union

from jenkinsapi.custom_exceptions import JenkinsAPIException

from .client import get_jenkins_client
from .utils import _to_dict
from ..cache import cache_manager as cache
import logging

logger = logging.getLogger(__name__)


def jenkins_get_queue() -> Union[List[Dict[str, Any]], Dict[str, str]]:
    """
    Get the current Jenkins build queue.
    
    Returns:
        List of queue item dictionaries or error dictionary
    """
    logger.debug("jenkins_get_queue called")
    
    # Check cache first
    cache_key = "jenkins:queue:current"
    cached = cache.get(cache_key)
    if cached:
        logger.debug(f"Returning cached result for {cache_key}")
        return cached
    
    j = get_jenkins_client()
    if j is None:
        logger.error("jenkins_get_queue: Jenkins client not initialized.")
        return {
            "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
        }
    
    try:
        queue = j.get_queue()
        result = [_to_dict(item) for item in queue]
        cache.set(cache_key, result, ttl=30)  # Cache for 30 seconds (queue changes frequently)
        return result
    except JenkinsAPIException as e:
        logger.error(f"jenkins_get_queue Jenkins Error: {e}", exc_info=True)
        return {"error": f"Jenkins API Error: {e}"}
    except Exception as e:
        logger.error(f"Unexpected error in jenkins_get_queue: {e}", exc_info=True)
        return {"error": f"An unexpected error occurred: {e}"}


def jenkins_get_queue_item(item_id: int) -> Union[Dict[str, Any], Dict[str, str]]:
    """
    Get detailed information about a specific queue item.
    
    Args:
        item_id: ID of the queue item
        
    Returns:
        Queue item dictionary or error dictionary
    """
    logger.debug(f"jenkins_get_queue_item called for item ID: {item_id}")
    
    if not isinstance(item_id, int) or item_id < 0:
        logger.error(f"Invalid queue item ID: {item_id}")
        return {"error": f"Invalid queue item ID: {item_id}"}
    
    # Check cache first
    cache_key = f"jenkins:queue_item:{item_id}"
    cached = cache.get(cache_key)
    if cached:
        logger.debug(f"Returning cached result for {cache_key}")
        return cached
    
    j = get_jenkins_client()
    if j is None:
        logger.error("jenkins_get_queue_item: Jenkins client not initialized.")
        return {
            "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
        }
    
    try:
        queue = j.get_queue()
        item = queue.get_queue_item(item_id)
        result = _to_dict(item)
        cache.set(cache_key, result, ttl=30)  # Cache for 30 seconds
        return result
    except JenkinsAPIException as e:
        if "No such queue item" in str(e):
            logger.warning(f"Queue item {item_id} not found.")
            return {"error": f"Queue item {item_id} not found."}
        logger.error(f"jenkins_get_queue_item Jenkins Error: {e}", exc_info=True)
        return {"error": f"Jenkins API Error: {e}"}
    except Exception as e:
        logger.error(f"Unexpected error in jenkins_get_queue_item: {e}", exc_info=True)
        return {"error": f"An unexpected error occurred: {e}"}


def jenkins_cancel_queue_item(item_id: int) -> Union[Dict[str, str], Dict[str, bool]]:
    """
    Cancel a queue item.
    
    Args:
        item_id: ID of the queue item to cancel
        
    Returns:
        Success dictionary or error dictionary
    """
    logger.debug(f"jenkins_cancel_queue_item called for item ID: {item_id}")
    
    if not isinstance(item_id, int) or item_id < 0:
        logger.error(f"Invalid queue item ID: {item_id}")
        return {"error": f"Invalid queue item ID: {item_id}"}
    
    j = get_jenkins_client()
    if j is None:
        logger.error("jenkins_cancel_queue_item: Jenkins client not initialized.")
        return {
            "error": "Jenkins client not initialized. Please set the JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN environment variables."
        }
    
    try:
        queue = j.get_queue()
        item = queue.get_queue_item(item_id)
        item.delete()
        
        # Clear queue cache since we modified the queue
        cache.delete("jenkins:queue:current")
        cache.delete(f"jenkins:queue_item:{item_id}")
        
        logger.info(f"Successfully canceled queue item {item_id}")
        return {"success": True, "message": f"Queue item {item_id} canceled successfully"}
    except JenkinsAPIException as e:
        if "No such queue item" in str(e):
            logger.warning(f"Queue item {item_id} not found.")
            return {"error": f"Queue item {item_id} not found."}
        logger.error(f"jenkins_cancel_queue_item Jenkins Error: {e}", exc_info=True)
        return {"error": f"Jenkins API Error: {e}"}
    except Exception as e:
        logger.error(f"Unexpected error in jenkins_cancel_queue_item: {e}", exc_info=True)
        return {"error": f"An unexpected error occurred: {e}"}