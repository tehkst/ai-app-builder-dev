from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class AgentManifest:
    agent_id: str
    department: str
    capabilities: List[str]
    owns_artifacts: List[str]
    accepts: List[str]
    produces: List[str]
    depends_on: List[str]
    parallelizable: bool
    approval_required: bool


MANIFESTS: Dict[str, AgentManifest] = {
    "ceo_agent": AgentManifest(
        agent_id="ceo_agent",
        department="executive",
        capabilities=["ceo_task"],
        owns_artifacts=[],
        accepts=["business_goal", "product_strategy"],
        produces=["strategic_direction"],
        depends_on=[],
        parallelizable=False,
        approval_required=False,
    ),
    "cto_agent": AgentManifest(
        agent_id="cto_agent",
        department="executive",
        capabilities=["cto_task"],
        owns_artifacts=[],
        accepts=["strategic_direction", "engineering_context"],
        produces=["technical_strategy"],
        depends_on=["ceo_agent"],
        parallelizable=False,
        approval_required=False,
    ),
    "engineering_manager_agent": AgentManifest(
        agent_id="engineering_manager_agent",
        department="engineering_management",
        capabilities=["engineering_manager_task"],
        owns_artifacts=[],
        accepts=["technical_strategy", "task_graph"],
        produces=["delegation_plan"],
        depends_on=["cto_agent"],
        parallelizable=True,
        approval_required=False,
    ),
    "backend_manager_agent": AgentManifest(
        agent_id="backend_manager_agent",
        department="backend",
        capabilities=["backend_manager_task"],
        owns_artifacts=[],
        accepts=["delegation_plan"],
        produces=["backend_assignment"],
        depends_on=["engineering_manager_agent"],
        parallelizable=True,
        approval_required=False,
    ),
    "frontend_manager_agent": AgentManifest(
        agent_id="frontend_manager_agent",
        department="frontend",
        capabilities=["frontend_manager_task"],
        owns_artifacts=[],
        accepts=["delegation_plan"],
        produces=["frontend_assignment"],
        depends_on=["engineering_manager_agent"],
        parallelizable=True,
        approval_required=False,
    ),
    "database_manager_agent": AgentManifest(
        agent_id="database_manager_agent",
        department="database",
        capabilities=["database_manager_task"],
        owns_artifacts=[],
        accepts=["delegation_plan"],
        produces=["database_assignment"],
        depends_on=["engineering_manager_agent"],
        parallelizable=True,
        approval_required=False,
    ),
    "quality_manager_agent": AgentManifest(
        agent_id="quality_manager_agent",
        department="quality",
        capabilities=["quality_manager_task"],
        owns_artifacts=[],
        accepts=["delegation_plan", "generated_artifacts"],
        produces=["quality_assignment"],
        depends_on=["engineering_manager_agent"],
        parallelizable=True,
        approval_required=False,
    ),
    "architect_agent": AgentManifest(
        agent_id="architect_agent",
        department="architecture",
        capabilities=["architect_task"],
        owns_artifacts=[],
        accepts=["scope_contract"],
        produces=["architecture_plan"],
        depends_on=[],
        parallelizable=False,
        approval_required=False,
    ),
    "backend_builder_agent": AgentManifest(
        agent_id="backend_builder_agent",
        department="backend",
        capabilities=["backend_builder_task"],
        owns_artifacts=[
            "generated/backend/service.py",
            "generated/backend/routes.py",
            "generated/backend/tests/test_routes.py",
        ],
        accepts=["architecture_plan"],
        produces=["backend_preview"],
        depends_on=["architect_agent"],
        parallelizable=True,
        approval_required=True,
    ),
    "code_steward_agent": AgentManifest(
        agent_id="code_steward_agent",
        department="quality",
        capabilities=["code_steward_task", "modularity_review_task"],
        owns_artifacts=[],
        accepts=["generated_artifacts", "module_graph", "quality_policy"],
        produces=["modularity_report", "refactor_recommendations"],
        depends_on=["reviewer_agent"],
        parallelizable=True,
        approval_required=False,
    ),
    "database_builder_agent": AgentManifest(
        agent_id="database_builder_agent",
        department="database",
        capabilities=["database_builder_task"],
        owns_artifacts=[
            "generated/manifest.json",
            "generated/backend/models.py",
            "generated/backend/schemas.py",
            "README.md",
        ],
        accepts=["architecture_plan"],
        produces=["database_preview"],
        depends_on=["architect_agent"],
        parallelizable=True,
        approval_required=True,
    ),
    "frontend_builder_agent": AgentManifest(
        agent_id="frontend_builder_agent",
        department="frontend",
        capabilities=["frontend_builder_task"],
        owns_artifacts=[
            "generated/manifest.json",
            "generated/frontend/App.jsx",
            "generated/frontend/package.json",
            "index.html",
            "styles.css",
            "app.js",
            "README.md",
        ],
        accepts=["backend_preview"],
        produces=["frontend_preview"],
        depends_on=["backend_builder_agent"],
        parallelizable=False,
        approval_required=True,
    ),
    "reviewer_agent": AgentManifest(
        agent_id="reviewer_agent",
        department="quality",
        capabilities=["reviewer_task"],
        owns_artifacts=[],
        accepts=["test_plan", "generated_artifacts"],
        produces=["review_report"],
        depends_on=["test_agent"],
        parallelizable=False,
        approval_required=False,
    ),
    "test_agent": AgentManifest(
        agent_id="test_agent",
        department="quality",
        capabilities=["test_task", "worker_loop_test"],
        owns_artifacts=[],
        accepts=["backend_preview", "database_preview", "frontend_preview"],
        produces=["test_plan"],
        depends_on=["backend_builder_agent", "database_builder_agent", "frontend_builder_agent"],
        parallelizable=False,
        approval_required=False,
    ),
}


def all_manifests() -> Dict[str, AgentManifest]:
    merged = dict(MANIFESTS)
    merged.update(_db_agent_manifests())
    return merged


def _db_agent_manifests() -> Dict[str, AgentManifest]:
    """Project admin-created (PlatformAgentDefinition) agents into manifest shape.

    Read-only, live query - lets organisation_console._workers() resolve department_id and
    reports_to for admin-created agents through its existing manifest-based fallback, without
    those agents needing a hand-authored, code-defined manifest entry.
    """
    import json

    from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
    from app.platform.persistence.models import PlatformAgentDefinition

    create_platform_tables()
    manifests: Dict[str, AgentManifest] = {}
    db = PlatformSessionLocal()
    try:
        rows = db.query(PlatformAgentDefinition).filter(PlatformAgentDefinition.status == "active").all()
        for row in rows:
            if row.agent_id in MANIFESTS:
                continue
            try:
                capabilities = json.loads(row.capabilities_json or "[]")
            except json.JSONDecodeError:
                capabilities = []
            try:
                metadata = json.loads(row.metadata_json or "{}")
            except json.JSONDecodeError:
                metadata = {}
            department = str(metadata.get("department_id") or "unassigned")
            reports_to = metadata.get("reports_to")
            manifests[row.agent_id] = AgentManifest(
                agent_id=row.agent_id,
                department=department,
                capabilities=[str(item) for item in capabilities if str(item).strip()],
                owns_artifacts=[],
                accepts=[],
                produces=[],
                depends_on=[str(reports_to)] if reports_to else [],
                parallelizable=True,
                approval_required=bool(row.requires_approval_for_new_tasks),
            )
    finally:
        db.close()
    return manifests


def get_manifest(agent_id: str) -> Optional[AgentManifest]:
    return MANIFESTS.get(agent_id)


def find_agents_by_capability(capability: str) -> List[AgentManifest]:
    return [manifest for manifest in MANIFESTS.values() if capability in manifest.capabilities]


def preferred_agent_id_for_capability(capability: str) -> Optional[str]:
    matches = find_agents_by_capability(capability)
    if not matches:
        return None
    return sorted(matches, key=lambda manifest: manifest.agent_id)[0].agent_id


def capability_to_agent_map() -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for manifest in sorted(MANIFESTS.values(), key=lambda item: item.agent_id):
        for capability in manifest.capabilities:
            mapping.setdefault(capability, manifest.agent_id)
    return mapping


def safe_execution_agent_ids() -> List[str]:
    return sorted(MANIFESTS.keys())


def artifact_owner(path: str) -> Optional[AgentManifest]:
    for manifest in MANIFESTS.values():
        if path in manifest.owns_artifacts:
            return manifest
    return None


def artifact_owner_map() -> Dict[str, str]:
    ownership: Dict[str, str] = {}
    for manifest in MANIFESTS.values():
        for artifact_path in manifest.owns_artifacts:
            ownership.setdefault(artifact_path, manifest.agent_id)
    return dict(sorted(ownership.items()))
