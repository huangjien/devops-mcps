"""GitHub issues operations module.

This module provides functions for interacting with GitHub issues,
including retrieving issue details, listing issues, and getting issue content.
"""

import logging
from typing import Any, Dict

from github.GithubException import GithubException, UnknownObjectException

from .cache import github_cache
from .github_client import get_github_client
from .github_serializers import _to_dict, _handle_paginated_list
from .inputs import (
    GetIssueContentInput, GetIssueDetailsInput, ListIssuesInput
)

logger = logging.getLogger(__name__)


@github_cache(expire=300)
def gh_get_issue_content(input_data: GetIssueContentInput) -> Dict[str, Any]:
    """
    Get the content of a GitHub issue including details and comments.
    
    Args:
        input_data: GetIssueContentInput containing repository and issue information.
        
    Returns:
        Dict[str, Any]: Issue content including details and comments.
        
    Raises:
        UnknownObjectException: If the repository or issue is not found.
        GithubException: If the GitHub API request fails.
    """
    try:
        g = get_github_client()
        repo = g.get_repo(f"{input_data.owner}/{input_data.repo}")
        issue = repo.get_issue(input_data.issue_number)
        
        # Get issue details
        issue_data = {
            "number": issue.number,
            "title": issue.title,
            "body": issue.body or "",
            "state": issue.state,
            "user": _to_dict(issue.user),
            "labels": [_to_dict(label) for label in issue.labels],
            "assignees": [_to_dict(assignee) for assignee in issue.assignees],
            "milestone": _to_dict(issue.milestone) if issue.milestone else None,
            "created_at": issue.created_at.isoformat() if issue.created_at else None,
            "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
            "closed_at": issue.closed_at.isoformat() if issue.closed_at else None,
            "url": issue.url,
            "html_url": issue.html_url,
            "comments_count": issue.comments
        }
        
        # Get comments if requested
        comments_data = []
        if input_data.include_comments:
            comments = issue.get_comments()
            max_comments = input_data.max_comments or 50
            
            comment_count = 0
            for comment in comments:
                if comment_count >= max_comments:
                    break
                
                comment_data = {
                    "id": comment.id,
                    "user": _to_dict(comment.user),
                    "body": comment.body or "",
                    "created_at": comment.created_at.isoformat() if comment.created_at else None,
                    "updated_at": comment.updated_at.isoformat() if comment.updated_at else None,
                    "url": comment.url,
                    "html_url": comment.html_url
                }
                comments_data.append(comment_data)
                comment_count += 1
        
        return {
            "issue": issue_data,
            "comments": comments_data
        }
    
    except UnknownObjectException as e:
        logger.error(f"Issue #{input_data.issue_number} not found: {e}")
        return {"error": f"Issue #{input_data.issue_number} not found"}
    except GithubException as e:
        logger.error(f"GitHub API error in get_issue_content: {e}")
        status_code = getattr(e, 'status', 'Unknown')
        data = getattr(e, 'data', {})
        if isinstance(data, dict):
            message = data.get('message', 'Unknown GitHub error')
        elif isinstance(data, str):
            message = data
        else:
            message = 'Unknown GitHub error'
        return {"error": f"GitHub API error: {status_code} - {message}"}
    except Exception as e:
        logger.error(f"Unexpected error in get_issue_content: {e}")
        return {"error": f"unexpected error: {e}"}


@github_cache(expire=300)
def gh_list_issues(input_data: ListIssuesInput) -> Dict[str, Any]:
    """
    List issues from a GitHub repository with filtering and sorting options.
    
    Args:
        input_data: ListIssuesInput containing repository and filtering parameters.
        
    Returns:
        Dict[str, Any]: List of issues with metadata.
        
    Raises:
        UnknownObjectException: If the repository is not found.
        GithubException: If the GitHub API request fails.
    """
    try:
        g = get_github_client()
        repo = g.get_repo(f"{input_data.owner}/{input_data.repo}")
        
        # Build filter parameters
        kwargs = {}
        
        if input_data.state:
            kwargs["state"] = input_data.state
        
        if input_data.labels:
            kwargs["labels"] = input_data.labels
        
        if input_data.sort:
            kwargs["sort"] = input_data.sort
        
        if input_data.direction:
            kwargs["direction"] = input_data.direction
        
        if input_data.since:
            kwargs["since"] = input_data.since
        
        if input_data.assignee:
            kwargs["assignee"] = input_data.assignee
        
        if input_data.creator:
            kwargs["creator"] = input_data.creator
        
        if input_data.mentioned:
            kwargs["mentioned"] = input_data.mentioned
        
        if input_data.milestone:
            if input_data.milestone == "none":
                kwargs["milestone"] = "none"
            elif input_data.milestone == "*":
                kwargs["milestone"] = "*"
            else:
                # Assume it's a milestone number
                try:
                    milestone_number = int(input_data.milestone)
                    milestone = repo.get_milestone(milestone_number)
                    kwargs["milestone"] = milestone
                except (ValueError, UnknownObjectException):
                    logger.warning(f"Invalid milestone: {input_data.milestone}")
        
        # Get issues
        issues = repo.get_issues(**kwargs)
        
        # Convert to list with pagination
        max_items = input_data.per_page or 30
        items = _handle_paginated_list(issues, max_items=max_items)
        
        return {
            "total_count": len(items),  # Note: GitHub API doesn't provide total count for repo issues
            "items": items
        }
    
    except ValueError as e:
        logger.error(f"GitHub client error in list_issues: {e}")
        return {"error": str(e)}
    except UnknownObjectException as e:
        logger.error(f"Repository not found: {e}")
        return {"error": f"Repository not found: {e}"}
    except GithubException as e:
        logger.error(f"GitHub API error in list_issues: {e}")
        status_code = getattr(e, 'status', 'Unknown')
        message = getattr(e, 'data', {}).get('message', 'Unknown GitHub error') if hasattr(e, 'data') and e.data else 'Unknown GitHub error'
        return {"error": f"GitHub API Error: {status_code} - {message}"}
    except Exception as e:
        logger.error(f"Unexpected error in list_issues: {e}")
        return {"error": f"unexpected error: {e}"}


@github_cache(expire=300)
def gh_get_issue_details(input_data: GetIssueDetailsInput) -> Dict[str, Any]:
    """
    Get detailed information about a specific GitHub issue.
    
    Args:
        input_data: GetIssueDetailsInput containing repository and issue information.
        
    Returns:
        Dict[str, Any]: Detailed issue information.
        
    Raises:
        UnknownObjectException: If the repository or issue is not found.
        GithubException: If the GitHub API request fails.
    """
    try:
        g = get_github_client()
        repo = g.get_repo(f"{input_data.owner}/{input_data.repo}")
        issue = repo.get_issue(input_data.issue_number)
        
        # Get basic issue information
        issue_details = {
            "title": issue.title,
            "labels": [label.name for label in issue.labels],
            "timestamp": issue.created_at.isoformat() if issue.created_at else None,
            "description": issue.body or "",
            "state": issue.state,
            "number": issue.number,
            "user": _to_dict(issue.user),
            "assignees": [_to_dict(assignee) for assignee in issue.assignees],
            "milestone": _to_dict(issue.milestone) if issue.milestone else None,
            "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
            "closed_at": issue.closed_at.isoformat() if issue.closed_at else None,
            "url": issue.url,
            "html_url": issue.html_url,
            "comments_count": issue.comments
        }
        
        # Note: gh_get_issue_details only returns basic issue information
        # For comments, use gh_get_issue_content instead
        
        return issue_details
    
    except ValueError as e:
        logger.error(f"GitHub client error in get_issue_details: {e}")
        return {"error": str(e)}
    except UnknownObjectException as e:
        logger.error(f"Repository or issue not found: {e}")
        return {"error": f"Repository or issue not found: {e}"}
    except GithubException as e:
        logger.error(f"GitHub API error in get_issue_details: {e}")
        status_code = getattr(e, 'status', 'Unknown')
        message = getattr(e, 'data', {}).get('message', 'Unknown GitHub error') if hasattr(e, 'data') and e.data else 'Unknown GitHub error'
        return {"error": f"GitHub API Error: {status_code} - {message}"}
    except Exception as e:
        logger.error(f"Unexpected error in get_issue_details: {e}")
        return {"error": f"unexpected error: {e}"}