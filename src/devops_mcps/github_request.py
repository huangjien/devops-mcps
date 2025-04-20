import os
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel


# Constants and configuration
GITHUB_API_BASE = "https://api.github.com"
GITHUB_TOKEN = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")


async def github_request(
    method: str,
    endpoint: str,
    data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Make a request to GitHub API with proper authentication and error handling."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "MCP-GitHub-Server/1.0",
    }

    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    url = f"{GITHUB_API_BASE}{endpoint}"

    async with httpx.AsyncClient() as client:
        try:
            if method == "GET":
                response = await client.get(
                    url, headers=headers, \
                        params=params, timeout=30.0
                )
            elif method == "POST":
                response = await client.post(
                    url, headers=headers, \
                        json=data, timeout=30.0
                )
            elif method == "PUT":
                response = await client.put(
                    url, headers=headers, \
                        json=data, timeout=30.0
                )
            elif method == "PATCH":
                response = await client.patch(
                    url, headers=headers, \
                        json=data, timeout=30.0
                )
            else:
                return {"error": f"Unsupported method: {method}"}

            response.raise_for_status()
            return response.json() if response.text else {}
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error {e.response.status_code}"
            try:
                error_json = e.response.json()
                if "message" in error_json:
                    error_message += f": {error_json['message']}"
            except:
                pass
            return {"error": error_message}
        except Exception as e:
            return {"error": str(e)}


# Define Pydantic models for input validation
class SearchRepositoriesInput(BaseModel):
    query: str
    page: int = 1
    per_page: int = 30


class CreateRepositoryInput(BaseModel):
    name: str
    description: str = ""
    private: bool = False
    autoInit: bool = False


class GetFileContentsInput(BaseModel):
    owner: str
    repo: str
    path: str
    branch: Optional[str] = None


class CreateOrUpdateFileInput(BaseModel):
    owner: str
    repo: str
    path: str
    content: str
    message: str
    branch: str
    sha: Optional[str] = None


class CreateIssueInput(BaseModel):
    owner: str
    repo: str
    title: str
    body: str = ""
    assignees: Optional[List[str]] = None
    labels: Optional[List[str]] = None
    milestone: Optional[int] = None


class ListIssuesInput(BaseModel):
    owner: str
    repo: str
    state: str = "open"
    labels: Optional[List[str]] = []
    sort: str = "created"
    direction: str = "desc"
    page: int = 1
    per_page: int = 30


class CreateCommentInput(BaseModel):
    owner: str
    repo: str
    sha: Optional[str] = None
    body: str = ""


class ListCommitsInput(BaseModel):
    owner: str
    repo: str
    branch: Optional[str] = None
    sha: Optional[str] = None
    per_page: int = 30
    page: int = 1


class CreatePullRequestInput(BaseModel):
    owner: str
    repo: str
    title: str
    head: str
    base: str
    body: str = ""
    draft: bool = False
    maintainer_can_modify: bool = True


class GetRepositoryInput(BaseModel):
    owner: str
    repo: str


class ForkRepositoryInput(BaseModel):
    owner: str
    repo: str
    organization: Optional[str] = None


class CreateBranchInput(BaseModel):
    owner: str
    repo: str
    branch: str
    from_branch: Optional[str] = None


class SearchCodeInput(BaseModel):
    q: str
    sort: str = "indexed"
    order: str = "desc"
    per_page: int = 30
    page: int = 1
