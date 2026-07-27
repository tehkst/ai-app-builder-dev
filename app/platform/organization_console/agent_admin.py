from __future__ import annotations

import json
import re
import uuid
from typing import Any, Dict, List, Optional

from app.platform.agents.generic_agent import build_generic_agent_handler
from app.platform.agents.manifest_registry import all_manifests
from app.platform.agents.registry import AgentDefinition, get_agent, list_agents, register_agent
from app.platform.auth.service import require_founder
from app.platform.organization.registry import all_departments, teams_for_department
from app.platform.organization_console import CONTRACT
from app.platform.organization_console.skills import validate_skill_document
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformAgentDefinition, PlatformApprovalRequest, utc_now
from app.platform.services.agent_factory_registration_service import (
    SAFE_AGENT_ID_PATTERN,
    SAFE_CAPABILITY_PATTERN,
)

RISK_LEVELS = {"low", "medium", "high", "critical"}


def query_agent_admin_options(payload: Dict[str, Any]) -> Dict[str, Any]:
    founder = require_founder(payload)
    if not founder.get("authorized"):
        return {
            "contract": CONTRACT,
            "status": "unauthorised",
            "authenticated": False,
            "error": "Founder authentication is required for organisation admin options.",
        }
    create_platform_tables()
    departments = all_departments()
    return {
        "contract": CONTRACT,
        "status": "ready",
        "departments": [
            {
                "department_id": department.department_id,
                "name": department.name,
                "teams": [
                    {"team_id": team.team_id, "name": team.name}
                    for team in teams_for_department(department.department_id)
                ],
            }
            for department in departments.values()
        ],
        "reports_to_candidates": sorted(
            {item["agent_id"] for item in list_agents()} | set(all_manifests().keys())
        ),
        "risk_levels": sorted(RISK_LEVELS),
    }


def create_agent(payload: Dict[str, Any]) -> Dict[str, Any]:
    founder = require_founder(payload)
    if not founder.get("authorized"):
        return {
            "contract": CONTRACT,
            "status": "unauthorised",
            "authenticated": False,
            "error": "Founder authentication is required to create an agent.",
        }

    try:
        proposed = _validate_input(payload)
    except ValueError as exc:
        return {"contract": CONTRACT, "status": "invalid", "error": str(exc)}

    create_platform_tables()
    db = PlatformSessionLocal()
    try:
        agent_id = _unique_agent_id(db, proposed["agent_id"])
        if get_agent(agent_id) or db.query(PlatformAgentDefinition).filter(
            PlatformAgentDefinition.agent_id == agent_id
        ).first():
            return {"contract": CONTRACT, "status": "conflict", "error": "Agent id already exists: %s" % agent_id}

        approval = PlatformApprovalRequest(
            approval_id="approval_%s" % uuid.uuid4().hex,
            title="Create specialist agent: %s" % proposed["name"],
            description=proposed["description"],
            status="approved",
            risk_level=proposed["risk_level"],
            requested_by=founder.get("email") or "founder",
            approver_id=founder.get("email") or "founder",
            source_type="agent_factory",
            source_id=None,
            action_type="create_specialist_agent",
            action_payload_json=json.dumps(
                {
                    "proposed_agent": {
                        "agent_id": agent_id,
                        "name": proposed["name"],
                        "description": proposed["description"],
                        "capabilities": proposed["capabilities"],
                        "risk_level": proposed["risk_level"],
                    },
                    "created_via": "organisation-console",
                },
                sort_keys=True,
            ),
            decision_note="Created directly by the founder through the Organisation console.",
            decided_at=utc_now(),
        )
        db.add(approval)

        db_agent = PlatformAgentDefinition(
            agent_id=agent_id,
            name=proposed["name"],
            description=proposed["description"],
            capabilities_json=json.dumps(proposed["capabilities"], sort_keys=True),
            risk_level=proposed["risk_level"],
            status="active",
            source_approval_id=approval.approval_id,
            source_type="agent_factory",
            safe_mode=True,
            writes_code=False,
            requires_approval_for_new_tasks=proposed["requires_approval_for_new_tasks"],
            metadata_json=json.dumps(
                {
                    "department_id": proposed["department_id"],
                    "team_id": proposed["team_id"],
                    "reports_to": proposed["reports_to"],
                    "created_by": founder.get("email") or "founder",
                },
                sort_keys=True,
            ),
        )
        db.add(db_agent)
        db.commit()
    finally:
        db.close()

    register_agent(
        AgentDefinition(
            agent_id=agent_id,
            name=proposed["name"],
            description=proposed["description"],
            capabilities=proposed["capabilities"],
            handler=build_generic_agent_handler(agent_id, proposed["name"], proposed["description"]),
            requires_approval_for_new_tasks=proposed["requires_approval_for_new_tasks"],
        )
    )

    _record_agent_creation_in_memory(proposed, founder_email=founder.get("email") or "founder")

    return {
        "contract": CONTRACT,
        "status": "created",
        "agent": {
            "agent_id": agent_id,
            "name": proposed["name"],
            "description": proposed["description"],
            "capabilities": proposed["capabilities"],
            "department_id": proposed["department_id"],
            "team_id": proposed["team_id"],
            "reports_to": proposed["reports_to"],
            "risk_level": proposed["risk_level"],
        },
        "github_execution_package": _initial_skill_package(agent_id, proposed),
        "governance": {
            "runtime_active": True,
            "skill_document_requires_pr": True,
            "note": (
                "The agent is already dispatchable using its description as a baseline. "
                "Submit the prepared skill document through governed repository execution "
                "to give it a richer, reviewed operating skill set."
            ),
        },
    }


def sync_db_agents_into_registry() -> Dict[str, Any]:
    """Load any active PlatformAgentDefinition rows not yet in this process's in-memory registry.

    Called on server startup so agents created (in a prior process, or a prior deploy)
    become dispatchable again after a restart. Agent creation itself already registers
    the agent immediately in the creating process via create_agent().
    """
    create_platform_tables()
    db = PlatformSessionLocal()
    loaded: List[str] = []
    try:
        rows = db.query(PlatformAgentDefinition).filter(PlatformAgentDefinition.status == "active").all()
        for row in rows:
            if get_agent(row.agent_id):
                continue
            try:
                capabilities = json.loads(row.capabilities_json or "[]")
            except json.JSONDecodeError:
                capabilities = []
            capabilities = [str(item) for item in capabilities if str(item).strip()]
            if not capabilities:
                continue
            register_agent(
                AgentDefinition(
                    agent_id=row.agent_id,
                    name=row.name,
                    description=row.description,
                    capabilities=capabilities,
                    handler=build_generic_agent_handler(row.agent_id, row.name, row.description),
                    requires_approval_for_new_tasks=bool(row.requires_approval_for_new_tasks),
                )
            )
            loaded.append(row.agent_id)
    finally:
        db.close()
    return {"loaded_agent_ids": loaded}


def _record_agent_creation_in_memory(proposed: Dict[str, Any], *, founder_email: str) -> None:
    """Best-effort structured-event ingestion into cognitive memory.

    Agent creation is a clean, non-hallucinated, already-validated event - exactly the kind
    of structured source cognitive_memory should prefer over free-text extraction. This must
    never block or fail agent creation itself, so failures here are swallowed.
    """
    try:
        from app.platform.cognitive_memory.edges import find_or_create_edge
        from app.platform.cognitive_memory.entities import find_or_create_entity
        from app.platform.cognitive_memory.episodes import record_episode

        create_platform_tables()
        with PlatformSessionLocal() as memory_db:
            agent_entity = find_or_create_entity(
                memory_db, tenant_id=None, name=proposed["name"], type_="agent",
                metadata={"agent_id": proposed["agent_id"], "created_by": founder_email},
            )
            department_entity = find_or_create_entity(
                memory_db, tenant_id=None, name=proposed["department_id"], type_="department",
            )
            find_or_create_edge(
                memory_db, tenant_id=None, source_entity_id=agent_entity.entity_id,
                target_entity_id=department_entity.entity_id, relationship="belongs_to_department",
            )
            if proposed["reports_to"]:
                manager_entity = find_or_create_entity(
                    memory_db, tenant_id=None, name=proposed["reports_to"], type_="agent",
                )
                find_or_create_edge(
                    memory_db, tenant_id=None, source_entity_id=agent_entity.entity_id,
                    target_entity_id=manager_entity.entity_id, relationship="reports_to",
                )
            record_episode(
                memory_db, tenant_id=None,
                content="Platform Admin %s created a new agent: %s (%s). %s" % (
                    founder_email, proposed["name"], proposed["agent_id"], proposed["description"],
                ),
                entity_references=[agent_entity.entity_id],
                source_type="agent_created", source_id=proposed["agent_id"],
            )
    except Exception:  # noqa: BLE001 - memory ingestion must never break agent creation
        pass


def _validate_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    name = str(payload.get("name") or "").strip()
    description = str(payload.get("description") or "").strip()
    department_id = str(payload.get("department_id") or "").strip()
    team_id = str(payload.get("team_id") or "").strip() or None
    reports_to = str(payload.get("reports_to") or "").strip() or None
    risk_level = str(payload.get("risk_level") or "medium").strip().lower()
    requires_approval = payload.get("requires_approval_for_new_tasks")
    requires_approval = True if requires_approval is None else bool(requires_approval)

    if len(name) < 2 or len(name) > 80:
        raise ValueError("Name must be between 2 and 80 characters.")
    if len(description) < 10 or len(description) > 2000:
        raise ValueError("Description must be between 10 and 2000 characters.")
    if risk_level not in RISK_LEVELS:
        raise ValueError("Unsupported risk_level: %s" % risk_level)

    departments = all_departments()
    if department_id not in departments:
        raise ValueError("Unknown department_id: %s" % department_id)
    if team_id:
        valid_team_ids = {team.team_id for team in teams_for_department(department_id)}
        if team_id not in valid_team_ids:
            raise ValueError("team_id does not belong to department %s: %s" % (department_id, team_id))
    if reports_to:
        known_agent_ids = {item["agent_id"] for item in list_agents()} | set(all_manifests().keys())
        if reports_to not in known_agent_ids:
            raise ValueError("reports_to does not reference a known agent: %s" % reports_to)

    capabilities = _clean_capabilities(payload.get("capabilities"), fallback_slug=_slug(name))
    agent_id = _slug(name) + "_agent"
    if not SAFE_AGENT_ID_PATTERN.match(agent_id):
        raise ValueError("Could not derive a safe agent id from the given name.")

    return {
        "agent_id": agent_id,
        "name": name,
        "description": description,
        "department_id": department_id,
        "team_id": team_id,
        "reports_to": reports_to,
        "risk_level": risk_level,
        "requires_approval_for_new_tasks": requires_approval,
        "capabilities": capabilities,
    }


def _clean_capabilities(raw: Any, fallback_slug: str) -> List[str]:
    values = raw if isinstance(raw, list) else []
    cleaned: List[str] = []
    for item in values:
        candidate = _slug(str(item)) + "_task"
        if SAFE_CAPABILITY_PATTERN.match(candidate) and candidate not in cleaned:
            cleaned.append(candidate)
    if not cleaned:
        cleaned = ["%s_task" % fallback_slug]
    return cleaned


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.lower()).strip("_")
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned or "custom"


def _unique_agent_id(db, base_agent_id: str) -> str:
    candidate = base_agent_id
    suffix = 2
    while get_agent(candidate) or db.query(PlatformAgentDefinition).filter(
        PlatformAgentDefinition.agent_id == candidate
    ).first():
        candidate = "%s_%d_agent" % (base_agent_id[: -len("_agent")], suffix)
        suffix += 1
        if suffix > 50:
            raise ValueError("Could not find a unique agent id.")
    return candidate


def _initial_skill_package(agent_id: str, proposed: Dict[str, Any]) -> Dict[str, Any]:
    content = (
        "# %s\n\n"
        "## Purpose\n%s\n\n"
        "## Capabilities\n%s\n\n"
        "## Operating boundaries\n"
        "- This agent may only produce analysis, plans, and draft text.\n"
        "- This agent cannot write files, merge code, deploy, or perform any governed action directly.\n"
        "- All outputs remain subject to founder review before being acted upon.\n"
    ) % (
        proposed["name"],
        proposed["description"],
        "\n".join("- %s" % capability for capability in proposed["capabilities"]),
    )
    validation = validate_skill_document(content)
    path = "app/platform/agents/skills/%s/skills.md" % agent_id
    return {
        "mission_id": "AFOS-017A-SKILL-%s" % agent_id.upper(),
        "title": "Add %s operational skills" % agent_id,
        "branch_name": "organisation-agent-%s-create" % agent_id.replace("_", "-"),
        "commit_message": "docs(skills): add %s operational skills" % agent_id,
        "pr_title": "Add %s operational skills" % agent_id,
        "pr_body": (
            "Governed Organisation Console agent creation.\n\n"
            "The agent is already active in the runtime registry using its description as a "
            "baseline. This change adds its reviewed operational skill document. Runtime "
            "activation of the richer skill content requires merge, release and verification."
        ),
        "file_changes": [{"path": path, "operation": "write", "content": content}],
        "live_execution": False,
        "approval_phrase": "",
        "validation": validation,
    }
