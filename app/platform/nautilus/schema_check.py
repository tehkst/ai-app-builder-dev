"""Minimal JSON-schema validation for recipe final output.

Supports the subset recipes need (type, required, properties, items, enum). The project has
no jsonschema dependency; unsupported keywords are ignored rather than guessed at.
"""
from __future__ import annotations

from typing import Any, Dict, List

TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def schema_errors(value: Any, schema: Dict[str, Any], path: str = "$") -> List[str]:
    errors: List[str] = []
    expected = schema.get("type")
    if isinstance(expected, str) and expected in TYPE_CHECKS and not TYPE_CHECKS[expected](value):
        return [f"{path} should be {expected}"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path} should be one of {schema['enum']}")
    if isinstance(value, dict):
        for key in schema.get("required") or []:
            if key not in value:
                errors.append(f"{path}.{key} is required")
        for key, sub_schema in (schema.get("properties") or {}).items():
            if key in value and isinstance(sub_schema, dict):
                errors.extend(schema_errors(value[key], sub_schema, f"{path}.{key}"))
    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        for index, item in enumerate(value):
            errors.extend(schema_errors(item, schema["items"], f"{path}[{index}]"))
    return errors
