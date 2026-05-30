from typing import List
from pydantic import BaseModel


class FilePlanItem(BaseModel):
    file_path: str
    file_type: str
    purpose: str


class FilePlan(BaseModel):
    files: List[FilePlanItem]
