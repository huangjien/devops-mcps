# /Users/huangjien/workspace/devops-mcps/src/devops_mcps/inputs.py
from pydantic import BaseModel
from typing import List, Optional


class ListArtifactoryItemsInput(BaseModel):
  repository: str
  path: str = "/"


class SearchArtifactoryItemsInput(BaseModel):
  query: str
  repositories: Optional[List[str]] = None


class GetArtifactoryItemInfoInput(BaseModel):
  repository: str
  path: str
