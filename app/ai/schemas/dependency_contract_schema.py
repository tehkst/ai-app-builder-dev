from typing import List
from pydantic import BaseModel


class DependencyIssue(BaseModel):
    severity: str
    dependency_type: str
    producer: str
    consumer: str
    issue: str


class DependencyReport(BaseModel):
    passed: bool
    issues: List[DependencyIssue]
