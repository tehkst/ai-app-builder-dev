from typing import List
from pydantic import BaseModel


class ExportedSymbol(BaseModel):
    file_path: str
    symbol_name: str
    symbol_type: str
    purpose: str


class ApiEndpoint(BaseModel):
    method: str
    path: str
    purpose: str
    request_schema: str
    response_schema: str


class InterfaceContract(BaseModel):
    exported_symbols: List[ExportedSymbol]
    api_endpoints: List[ApiEndpoint]
