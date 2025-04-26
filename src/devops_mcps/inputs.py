# /Users/huangjien/workspace/devops-mcps/src/devops_mcps/inputs.py
from pydantic import BaseModel, field_validator
from typing import List, Optional


class SearchRepositoriesInput(BaseModel):
  query: str


class GetFileContentsInput(BaseModel):
  owner: str
  repo: str
  path: str
  branch: Optional[str] = None


class ListCommitsInput(BaseModel):
  owner: str
  repo: str
  branch: Optional[str] = None


class ListIssuesInput(BaseModel):
  owner: str
  repo: str
  state: str = "open"
  labels: Optional[List[str]] = None
  sort: str = "created"
  direction: str = "desc"

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


class GetRepositoryInput(BaseModel):
  owner: str
  repo: str


class SearchCodeInput(BaseModel):
  q: str
  sort: str = "indexed"
  order: str = "desc"

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


class ListArtifactoryItemsInput(BaseModel):
  repository: str
  path: str = "/"


class SearchArtifactoryItemsInput(BaseModel):
  query: str
  repositories: Optional[List[str]] = None


class GetArtifactoryItemInfoInput(BaseModel):
  repository: str
  path: str
