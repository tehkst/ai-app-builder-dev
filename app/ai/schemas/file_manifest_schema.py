from typing import List
from pydantic import BaseModel


class GeneratedFile(BaseModel):
    file_path: str
    file_type: str
    purpose: str
    content: str


class FileManifest(BaseModel):
    files: List[GeneratedFile]
