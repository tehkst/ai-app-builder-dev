from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class MemoryScope:
    scope_id: str
    owner_type: str
    owner_id: str
    description: str
    allowed_entries: List[str]
    visibility: str


MEMORY_SCOPES: Dict[str, MemoryScope] = {
    "executive_management_memory": MemoryScope(
        scope_id="executive_management_memory",
        owner_type="department",
        owner_id="executive",
        description="Executive strategy, prioritization, and technical direction.",
        allowed_entries=["strategy_decision", "priority_decision", "technical_directive"],
        visibility="department",
    ),
    "engineering_management_memory": MemoryScope(
        scope_id="engineering_management_memory",
        owner_type="department",
        owner_id="engineering_management",
        description="Mission coordination, delivery sequencing, and bottleneck evidence.",
        allowed_entries=["delivery_decision", "assignment_note", "bottleneck_note"],
        visibility="department",
    ),
    "organization_architecture_memory": MemoryScope(
        scope_id="organization_architecture_memory",
        owner_type="organization",
        owner_id="ai_software_factory",
        description="Organization-level architecture decisions and platform-wide engineering directives.",
        allowed_entries=["architecture_decision", "platform_directive", "operating_principle"],
        visibility="organization",
    ),
    "backend_department_memory": MemoryScope(
        scope_id="backend_department_memory",
        owner_type="department",
        owner_id="backend",
        description="Backend standards, service patterns, route conventions, and lessons learned.",
        allowed_entries=["coding_standard", "api_pattern", "service_pattern", "lesson_learned"],
        visibility="department",
    ),
    "database_department_memory": MemoryScope(
        scope_id="database_department_memory",
        owner_type="department",
        owner_id="database",
        description="Data modeling rules, schema conventions, relationship patterns, and persistence decisions.",
        allowed_entries=["schema_pattern", "relationship_rule", "migration_decision", "lesson_learned"],
        visibility="department",
    ),
    "frontend_department_memory": MemoryScope(
        scope_id="frontend_department_memory",
        owner_type="department",
        owner_id="frontend",
        description="Frontend component patterns, UI standards, accessibility rules, and design preferences.",
        allowed_entries=["ui_pattern", "component_standard", "accessibility_rule", "lesson_learned"],
        visibility="department",
    ),
    "quality_department_memory": MemoryScope(
        scope_id="quality_department_memory",
        owner_type="department",
        owner_id="quality",
        description="Review standards, regression history, release readiness criteria, and testing policy.",
        allowed_entries=["test_pattern", "review_rule", "regression_note", "release_criterion"],
        visibility="department",
    ),
    "architecture_team_memory": MemoryScope(
        scope_id="architecture_team_memory",
        owner_type="team",
        owner_id="architecture_core",
        description="Architecture team planning notes and scope translation heuristics.",
        allowed_entries=["planning_note", "scope_heuristic", "architecture_pattern"],
        visibility="team",
    ),
    "executive_leadership_memory": MemoryScope(
        scope_id="executive_leadership_memory",
        owner_type="team",
        owner_id="executive_leadership",
        description="Executive leadership decisions and company operating context.",
        allowed_entries=["strategy_note", "priority_note", "technical_direction"],
        visibility="team",
    ),
    "engineering_management_team_memory": MemoryScope(
        scope_id="engineering_management_team_memory",
        owner_type="team",
        owner_id="engineering_management_core",
        description="Engineering management coordination and delivery notes.",
        allowed_entries=["assignment_note", "delivery_note", "bottleneck_note"],
        visibility="team",
    ),
    "backend_team_memory": MemoryScope(
        scope_id="backend_team_memory",
        owner_type="team",
        owner_id="backend_core",
        description="Backend team implementation notes for services and routes.",
        allowed_entries=["implementation_note", "service_rule", "route_rule"],
        visibility="team",
    ),
    "database_team_memory": MemoryScope(
        scope_id="database_team_memory",
        owner_type="team",
        owner_id="database_core",
        description="Database team implementation notes for models and schemas.",
        allowed_entries=["implementation_note", "model_rule", "schema_rule"],
        visibility="team",
    ),
    "frontend_team_memory": MemoryScope(
        scope_id="frontend_team_memory",
        owner_type="team",
        owner_id="frontend_core",
        description="Frontend team implementation notes for UI previews.",
        allowed_entries=["implementation_note", "component_rule", "interaction_rule"],
        visibility="team",
    ),
    "quality_review_team_memory": MemoryScope(
        scope_id="quality_review_team_memory",
        owner_type="team",
        owner_id="quality_review",
        description="Review team checklists and quality heuristics.",
        allowed_entries=["review_note", "quality_gate", "checklist_item"],
        visibility="team",
    ),
    "quality_testing_team_memory": MemoryScope(
        scope_id="quality_testing_team_memory",
        owner_type="team",
        owner_id="quality_testing",
        description="Testing team validation patterns and release readiness notes.",
        allowed_entries=["test_note", "release_note", "regression_note"],
        visibility="team",
    ),
}


def all_memory_scopes() -> Dict[str, MemoryScope]:
    return dict(MEMORY_SCOPES)


def get_memory_scope(scope_id: str) -> Optional[MemoryScope]:
    return MEMORY_SCOPES.get(scope_id)


def memory_scopes_for_owner(owner_type: str, owner_id: str) -> List[MemoryScope]:
    return [
        scope
        for scope in MEMORY_SCOPES.values()
        if scope.owner_type == owner_type and scope.owner_id == owner_id
    ]
