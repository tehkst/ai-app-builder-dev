from typing import List
from pydantic import BaseModel, Field


class NonFunctionalRequirements(BaseModel):
    security: str
    scalability: str
    performance: str
    availability: str
    audit_logging: bool
    role_based_access_control: bool
    data_protection: str


class ProductSpec(BaseModel):
    app_name: str = Field(description="Short product name")
    summary: str = Field(description="Clear summary of the app")
    target_users: List[str]
    user_roles: List[str]
    core_features: List[str]
    pages: List[str]
    database_entities: List[str]
    api_modules: List[str]
    non_functional_requirements: NonFunctionalRequirements
    security_requirements: List[str]
    assumptions: List[str]
    risks: List[str]
    clarification_questions: List[str]
