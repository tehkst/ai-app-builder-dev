from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ExecutionContext:
    workflow_id: str
    task_id: str
    story_id: Optional[str]
    required_capability: str
    priority: int
    metadata: Dict[str, object]
    artifact_paths: List[str]
