import logging
import sys
import base64

import argparse
from typing import List
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

from devops_mcps.github_request import (
    GITHUB_TOKEN,
    GetFileContentsInput,
    GetRepositoryInput,
    ListIssuesInput,
    ListCommitsInput,
    SearchCodeInput,
    SearchRepositoriesInput,
    github_request,
)


logging.basicConfig(stream=sys.stderr, level=logging.INFO)

load_dotenv()

mcp = FastMCP("DevOps MCP Server", settings={"initialization_timeout": 10})

if not GITHUB_TOKEN:
    print("Warning: GITHUB_PERSONAL_ACCESS_TOKEN environment variable not set")
    print("Some functionality may be limited")


# Helper functions for GitHub API requests
# Github API Tools implementations
@mcp.tool()
async def search_repositories(query: str, page: int = 1, perPage: int = 30) -> str:
    """Search for GitHub repositories

    Args:
        query: Search query using GitHub search syntax
        page: Page number for pagination (default: 1)
        perPage: Results per page (max 100, default: 30)

    Returns:
        Formatted search results with repository details
    """
    # Validate inputs with Pydantic
    input_data = SearchRepositoriesInput(query=query, page=page, perPage=perPage)

    params = {
        "q": input_data.query,
        "page": input_data.page,
        "per_page": min(input_data.perPage, 100),  # Enforcing GitHub API limits
    }

    result = await github_request("GET", "/search/repositories", params=params)

    if "error" in result:
        return f"Error searching repositories: {result['error']}"

    total_count = result.get("total_count", 0)
    items = result.get("items", [])

    if not items:
        return f"No repositories found matching '{input_data.query}'."

    response = [
        f"Found {total_count} repositories matching '{input_data.query}'. \
              Showing page {input_data.page}:"
    ]

    for repo in items:
        description = repo.get("description", "No description")
        response.append(f"\n## {repo['full_name']}")
        response.append(f"Description: {description}")
        response.append(
            f"Stars: {repo.get('stargazers_count', 0)}, \
                Forks: {repo.get('forks_count', 0)}"
        )
        response.append(f"Language: {repo.get('language', 'Not specified')}")
        response.append(f"URL: {repo.get('html_url', 'N/A')}")

    return "\n".join(response)


@mcp.tool()
async def get_file_contents(
    owner: str, repo: str, path: str, branch: str = None
) -> str:
    """Get the contents of a file or directory from a GitHub repository.

    Args:
        owner: Repository owner (username or organization)
        repo: Repository name
        path: Path to file/directory
        branch: Branch to get contents from (default: repo default branch)

    Returns:
        File content or directory listing
    """
    # Validate inputs with Pydantic
    input_data = GetFileContentsInput(owner=owner, repo=repo, path=path, branch=branch)

    endpoint = f"/repos/{input_data.owner}/{input_data.repo}/contents/{input_data.path}"
    params = {}
    if input_data.branch:
        params["ref"] = input_data.branch

    result = await github_request("GET", endpoint, params=params)

    if "error" in result:
        return f"Error getting file contents: {result['error']}"

    # If result is a list, it's a directory
    if isinstance(result, list):
        response = [
            f"Directory listing for `{input_data.path}` in \
                {input_data.owner}/{input_data.repo}:"
        ]
        for item in result:
            if isinstance(item, dict):
                item_type = "📁 " if item.get("type") == "dir" else "📄 "
                response.append(
                    f"{item_type}{item.get('name', 'Unknown')} - \
                        {item.get('size', 0)} bytes"
                )
            else:
                response.append(f"📄 {item}")
        return "\n".join(response)

    # It's a file
    content = result.get("content", "")
    encoding = result.get("encoding", "")

    if encoding == "base64":

        try:
            decoded_content = base64.b64decode(content).decode("utf-8")
            return f"Contents of `{input_data.path}` in \
                {input_data.owner}/{input_data.repo}:\n\n```\n{decoded_content}\n```"
        except:
            return f"Could not decode content of `{input_data.path}`. \
                It may be a binary file."

    return f"Contents of `{input_data.path}` in {input_data.owner}/{input_data.repo} \
        (not in base64 format):\n{content}"


@mcp.tool()
async def list_commits(
    owner: str,
    repo: str,
    branch: str = None,
    sha: str = None,
    per_page: int = 30,
) -> str:
    """List commits in a GitHub repository
    Args:
        owner: Repository owner (username or organization)
        repo: Repository name
        branch: Branch to list commits from (default: repo default branch)
        sha: SHA to start listing commits from
        per_page: Results per page (max 100)
    Returns:
        Formatted list of commits
    """
    # Validate inputs with Pydantic
    input_data = ListCommitsInput(
        owner=owner, repo=repo, branch=branch, sha=sha, per_page=per_page
    )
    endpoint = f"/repos/{input_data.owner}/{input_data.repo}/commits"
    params = {
        "per_page": min(input_data.per_page, 100),  # Enforce GitHub API limits
        "sha": input_data.sha,
        "branch": input_data.branch,
    }

    endpoint = f"/repos/{input_data.owner}/{input_data.repo}/commits", {
        "per_page": min(input_data.per_page, 100),
        "sha": input_data.sha,
        "branch": input_data.branch,
    }
    result = await github_request("GET", endpoint, params=params)
    if "error" in result:
        return f"Error listing commits: {result['error']}"

    if not result:
        return f"No commits found in {input_data.owner}/{input_data.repo}."
    response = [
        f"Commits in {input_data.owner}/{input_data.repo} \
            (branch: {input_data.branch}, page: {input_data.page}):"
    ]
    for commit in result:
        if not isinstance(commit, dict):
            response.append(f"\n## Commit: {commit}")
            continue
        response.append(f"\n## {commit.get('sha', 'Unknown')}")
        response.append(
            f"Author: {commit.get('commit', {}).get('author', {})\
                       .get('name', 'Unknown')}"
        )
        response.append(
            f"Date: {commit.get('commit', {}).get('author', {}).get('date', 'Unknown')}"
        )
        response.append(
            f"Message: {commit.get('commit', {}).get('message', 'No message')}"
        )
        response.append(f"URL: {commit.get('html_url', 'N/A')}")
        response.append(f"Sha: {commit.get('sha', {}).get('sha', '{}')}")
    return "\n".join(response)


@mcp.tool()
async def list_issues(
    owner: str,
    repo: str,
    state: str = "open",
    labels: List[str] = [],
    sort: str = "created",
    direction: str = "desc",
    page: int = 1,
    per_page: int = 30,
) -> str:
    """List issues in a GitHub repository with filtering options

    Args:
        owner: Repository owner
        repo: Repository name
        state: Filter by state ('open', 'closed', 'all')
        labels: Filter by labels
        sort: Sort by ('created', 'updated', 'comments')
        direction: Sort direction ('asc', 'desc')
        page: Page number
        per_page: Results per page

    Returns:
        Formatted list of issues
    """
    # Validate inputs with Pydantic
    input_data = ListIssuesInput(
        owner=owner,
        repo=repo,
        state=state,
        labels=labels,
        sort=sort,
        direction=direction,
        page=page,
        per_page=per_page,
    )

    params = {
        "state": input_data.state,
        "sort": input_data.sort,
        "direction": input_data.direction,
        "page": input_data.page,
        "per_page": min(input_data.per_page, 100),  # Enforce GitHub API limits
    }

    if input_data.labels:
        params["labels"] = ",".join(input_data.labels)

    endpoint = f"/repos/{input_data.owner}/{input_data.repo}/issues"
    result = await github_request("GET", endpoint, params=params)

    if "error" in result:
        return f"Error listing issues: {result['error']}"

    if not result:
        return f"No issues found matching the criteria in \
            {input_data.owner}/{input_data.repo}."

    response = [
        f"Issues for {input_data.owner}/{input_data.repo}\
              (state: {input_data.state}, page: {input_data.page}):"
    ]

    for issue in result:
        if not isinstance(issue, dict):
            response.append(f"\n## Issue: {issue}")
            continue

        response.append(
            f"\n## #{issue.get('number', 'Unknown')} - {issue.get('title', 'Untitled')}"
        )
        response.append(f"State: {issue.get('state', 'Unknown')}")
        response.append(f"Created: {issue.get('created_at', 'Unknown')}")
        response.append(f"Updated: {issue.get('updated_at', 'Unknown')}")

        if issue.get("labels"):
            label_names = [
                label.get("name", "Unknown") for label in issue.get("labels", [])
            ]
            response.append(f"Labels: {', '.join(label_names)}")

        if issue.get("assignees"):
            assignee_names = [
                assignee.get("login", "Unknown")
                for assignee in issue.get("assignees", [])
            ]
            response.append(f"Assignees: {', '.join(assignee_names)}")

        response.append(f"URL: {issue.get('html_url', 'N/A')}")

    return "\n".join(response)


@mcp.tool()
async def get_repository(owner: str, repo: str) -> str:
    """Get information about a GitHub repository

    Args:
        owner: Repository owner (username or organization)
        repo: Repository name

    Returns:
        Formatted repository details
    """
    # Validate inputs with Pydantic
    input_data = GetRepositoryInput(owner=owner, repo=repo)

    endpoint = f"/repos/{input_data.owner}/{input_data.repo}"
    result = await github_request("GET", endpoint)

    if "error" in result:
        return f"Error getting repository information: {result['error']}"

    topics = result.get("topics", [])
    topics_str = ", ".join(topics) if topics else "None"

    return f"""
# Repository Info: {result.get('full_name', f'{input_data.owner}/{input_data.repo}')}

- Description: {result.get('description', 'No description')}
- URL: {result.get('html_url', 'N/A')}
- Homepage: {result.get('homepage', 'N/A')}
- Language: {result.get('language', 'Not specified')}
- Stars: {result.get('stargazers_count', 0)}
- Forks: {result.get('forks_count', 0)}
- Watchers: {result.get('watchers_count', 0)}
- Open Issues: {result.get('open_issues_count', 0)}
- License: {result.get('license', {}).get('name', 'Not specified') \
            if result.get('license') else 'Not specified'}
- Private: {'Yes' if result.get('private', False) else 'No'}
- Created: {result.get('created_at', 'Unknown')}
- Updated: {result.get('updated_at', 'Unknown')}
- Default Branch: {result.get('default_branch', 'Unknown')}
- Topics: {topics_str}
    """


@mcp.tool()
async def search_code(
    q: str,
    sort: str = "indexed",
    order: str = "desc",
    per_page: int = 30,
    page: int = 1,
) -> str:
    """Search for code across GitHub repositories.

    Args:
        q: Search query using GitHub code search syntax
        sort: Sort field ('indexed' only)
        order: Sort order ('asc' or 'desc')
        per_page: Results per page (max 100)
        page: Page number

    Returns:
        Formatted code search results
    """
    # Validate inputs with Pydantic
    input_data = SearchCodeInput(
        q=q, sort=sort, order=order, per_page=per_page, page=page
    )

    params = {
        "q": input_data.q,
        "sort": input_data.sort,
        "order": input_data.order,
        "per_page": min(input_data.per_page, 100),
        "page": input_data.page,
    }

    result = await github_request("GET", "/search/code", params=params)

    if "error" in result:
        return f"Error searching code: {result['error']}"

    total_count = result.get("total_count", 0)
    items = result.get("items", [])

    if not items:
        return f"No code found matching '{input_data.q}'."

    response = [
        f"Found {total_count} code results matching '{input_data.q}'. \
            Showing page {input_data.page}:"
    ]

    for item in items:
        repo = item.get("repository", {})
        repo_name = repo.get("full_name", "Unknown")
        path = item.get("path", "Unknown file")
        name = item.get("name", "Unknown")

        response.append(f"\n## {repo_name} - {path}")
        response.append(f"File: {name}")
        response.append(f"URL: {item.get('html_url', 'N/A')}")

    return "\n".join(response)


def main():
    """Entry point for the CLI."""
    parser = argparse.ArgumentParser(description="DevOps MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport type (stdio or sse)",
    )

    args = parser.parse_args()
    mcp.run(transport=args.transport)


def main_sse():
    """Run the MCP server with SSE transport."""

    sys.argv.extend(["--transport", "sse"])
    main()


if __name__ == "__main__":
    main()
