"""GitHub input classes module.

This module contains Pydantic models for GitHub API input validation.
"""

from pydantic import BaseModel, field_validator
from typing import List, Optional


class SearchRepositoriesInput(BaseModel):
    query: str
    sort: Optional[str] = "updated"
    order: Optional[str] = "desc"
    per_page: Optional[int] = 30
    page: Optional[int] = 1
    # Additional search filters
    language: Optional[str] = None
    user: Optional[str] = None
    org: Optional[str] = None
    topic: Optional[str] = None
    stars: Optional[str] = None
    forks: Optional[str] = None
    size: Optional[str] = None
    pushed: Optional[str] = None
    created: Optional[str] = None
    updated: Optional[str] = None
    license: Optional[str] = None
    is_public: Optional[bool] = None
    archived: Optional[bool] = None


class GetFileContentsInput(BaseModel):
    owner: str
    repo: str
    path: str
    branch: Optional[str] = None


class ListCommitsInput(BaseModel):
    owner: str
    repo: str
    branch: Optional[str] = None
    sha: Optional[str] = None
    path: Optional[str] = None
    author: Optional[str] = None
    since: Optional[str] = None
    until: Optional[str] = None
    per_page: Optional[int] = 30
    page: Optional[int] = 1


class ListIssuesInput(BaseModel):
    owner: str
    repo: str
    state: str = "open"
    labels: Optional[List[str]] = None
    sort: str = "created"
    direction: str = "desc"
    since: Optional[str] = None
    assignee: Optional[str] = None
    creator: Optional[str] = None
    mentioned: Optional[str] = None
    milestone: Optional[str] = None
    per_page: Optional[int] = 30
    page: Optional[int] = 1

    @field_validator("state")
    @classmethod
    def state_must_be_valid(cls, v: str) -> str:
        if v not in ["open", "closed", "all"]:
            raise ValueError("state must be 'open', 'closed', or 'all'")
        return v

    @field_validator("sort")
    @classmethod
    def sort_must_be_valid(cls, v: str) -> str:
        if v not in ["created", "updated", "comments"]:
            raise ValueError("sort must be 'created', 'updated', or 'comments'")
        return v

    @field_validator("direction")
    @classmethod
    def direction_must_be_valid(cls, v: str) -> str:
        if v not in ["asc", "desc"]:
            raise ValueError("direction must be 'asc' or 'desc'")
        return v


class GetIssueContentInput(BaseModel):
    owner: str
    repo: str
    issue_number: int
    include_comments: bool = True
    max_comments: Optional[int] = 50


class GetIssueDetailsInput(BaseModel):
    owner: str
    repo: str
    issue_number: int


class GetCurrentUserInfoInput(BaseModel):
    pass  # No parameters needed for current user info


class GetRepositoryInput(BaseModel):
    owner: str
    repo: str
    include_topics: Optional[bool] = False
    include_languages: Optional[bool] = False
    include_contributors: Optional[bool] = False
    max_contributors: Optional[int] = 10
    include_releases: Optional[bool] = False
    max_releases: Optional[int] = 5
    include_branches: Optional[bool] = False
    max_branches: Optional[int] = 10


class SearchCodeInput(BaseModel):
    q: str
    sort: str = "indexed"
    order: str = "desc"
    per_page: Optional[int] = 30
    page: Optional[int] = 1
    repo: Optional[str] = None
    language: Optional[str] = None
    filename: Optional[str] = None
    extension: Optional[str] = None
    path: Optional[str] = None
    size: Optional[str] = None
    user: Optional[str] = None
    org: Optional[str] = None

    @field_validator("sort")
    @classmethod
    def sort_must_be_valid(cls, v: str) -> str:
        return v

    @field_validator("order")
    @classmethod
    def order_must_be_valid(cls, v: str) -> str:
        if v not in ["asc", "desc"]:
            raise ValueError("order must be 'asc' or 'desc'")
        return v