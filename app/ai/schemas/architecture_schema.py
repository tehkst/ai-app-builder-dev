from pydantic import BaseModel
from typing import List


class ArchitectureSchema(BaseModel):

    app_type: str

    frontend_framework: str

    backend_framework: str

    database: str

    authentication: str

    pages: List[str]

    api_modules: List[str]

    database_tables: List[str]

    deployment_strategy: str
