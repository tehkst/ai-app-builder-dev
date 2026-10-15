"""Recipes: reusable, parameterised agent tasks (modelled on goose's recipe format).

A recipe is a YAML or JSON file::

    version: "1.0"
    title: Add health endpoint
    description: Adds GET /health to a generated FastAPI app
    instructions: You are a backend builder working in {{ app_name }}.   # system prompt
    prompt: Add a /health endpoint that returns {"status": "ok"}.         # the goal
    parameters:
      - {key: app_name, requirement: required, description: App name}
      - {key: port, requirement: optional, default: "8000"}
    max_turns: 30
    permission_mode: smart            # auto | smart | approve | read_only
    response:                         # optional structured final output
      json_schema: {type: object, required: [summary], properties: {summary: {type: string}}}
    retry:                            # optional success checks, run in the workspace
      max_retries: 2
      checks:
        - {type: shell, command: "python -m pytest -q"}
      on_failure: "rm -rf .pytest_cache"
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.platform.nautilus.permissions import PERMISSION_MODES

PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")


class RecipeError(ValueError):
    pass


@dataclass(frozen=True)
class RecipeParameter:
    key: str
    requirement: str = "required"  # "required" | "optional"
    default: Optional[str] = None
    description: str = ""


@dataclass(frozen=True)
class RetryConfig:
    max_retries: int = 0
    checks: List[str] = field(default_factory=list)  # shell commands that must exit 0
    on_failure: Optional[str] = None
    timeout_seconds: int = 300


@dataclass(frozen=True)
class Recipe:
    title: str
    description: str
    prompt: str
    instructions: str = ""
    parameters: List[RecipeParameter] = field(default_factory=list)
    max_turns: int = 25
    permission_mode: str = "approve"
    response_schema: Optional[Dict[str, Any]] = None
    retry: RetryConfig = field(default_factory=RetryConfig)
    version: str = "1.0"

    def resolve_parameters(self, values: Dict[str, Any]) -> Dict[str, str]:
        resolved: Dict[str, str] = {}
        missing: List[str] = []
        for parameter in self.parameters:
            if parameter.key in values and values[parameter.key] is not None:
                resolved[parameter.key] = str(values[parameter.key])
            elif parameter.default is not None:
                resolved[parameter.key] = str(parameter.default)
            elif parameter.requirement == "required":
                missing.append(parameter.key)
        if missing:
            raise RecipeError(f"Recipe '{self.title}' is missing required parameter(s): {', '.join(missing)}")
        return resolved

    def render(self, text: str, values: Dict[str, str]) -> str:
        def substitute(match: re.Match) -> str:
            key = match.group(1)
            if key not in values:
                raise RecipeError(f"Recipe '{self.title}' references undeclared parameter '{key}'.")
            return values[key]

        return PLACEHOLDER.sub(substitute, text)


def recipe_from_dict(data: Dict[str, Any]) -> Recipe:
    if not isinstance(data, dict):
        raise RecipeError("A recipe must be a mapping.")
    for key in ("title", "description", "prompt"):
        if not str(data.get(key) or "").strip():
            raise RecipeError(f"Recipe field '{key}' is required.")
    mode = str(data.get("permission_mode") or "approve")
    if mode not in PERMISSION_MODES:
        raise RecipeError(f"Recipe permission_mode must be one of {PERMISSION_MODES}.")
    parameters = []
    for raw in data.get("parameters") or []:
        if not isinstance(raw, dict) or not raw.get("key"):
            raise RecipeError("Each recipe parameter needs a 'key'.")
        requirement = str(raw.get("requirement") or "required")
        if requirement not in ("required", "optional"):
            raise RecipeError(f"Parameter '{raw['key']}' requirement must be 'required' or 'optional'.")
        default = raw.get("default")
        parameters.append(RecipeParameter(str(raw["key"]), requirement,
                                          None if default is None else str(default), str(raw.get("description") or "")))
    retry_raw = data.get("retry") or {}
    checks = [str(c.get("command") if isinstance(c, dict) else c) for c in retry_raw.get("checks") or []]
    retry = RetryConfig(int(retry_raw.get("max_retries") or 0), [c for c in checks if c.strip()],
                        retry_raw.get("on_failure"), int(retry_raw.get("timeout_seconds") or 300))
    response = data.get("response") or {}
    return Recipe(
        title=str(data["title"]), description=str(data["description"]), prompt=str(data["prompt"]),
        instructions=str(data.get("instructions") or ""), parameters=parameters,
        max_turns=int(data.get("max_turns") or 25), permission_mode=mode,
        response_schema=response.get("json_schema"), retry=retry, version=str(data.get("version") or "1.0"),
    )


def load_recipe(path: str) -> Recipe:
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    if source.suffix.lower() == ".json":
        return recipe_from_dict(json.loads(text))
    import yaml  # PyYAML ships with the langchain dependency set

    return recipe_from_dict(yaml.safe_load(text))
