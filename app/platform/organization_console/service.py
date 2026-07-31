from __future__ import annotations

import json
import re
import requests
import copy
from datetime import datetime, timezone
from threading import RLock
from time import monotonic
from typing import Any, Dict, Iterable, List, Optional

import app.platform.agents.specialists  # noqa: F401
from app.platform.agents.manifest_registry import all_manifests
from app.platform.agents.registry import get_agent, list_agents
from app.platform.auth.service import require_founder
from app.platform.management.registry import all_management_roles
from app.platform.organization.registry import all_departments, all_teams
from app.platform.organization_console import CONTRACT
from app.platform.organization_console.evidence import (
    build_runtime_index,
    project_worker_assignments,
    project_worker_evidence,
    task_agent_id,
)
from app.platform.organization_console.skills import (
    active_skill_diagnostic,
    read_skill_document,
    read_skill_version,
    skill_history,
    validate_skill_document,
)
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformAuditEvent
from app.core.email import email_configured, send_email
ACTIVE = {"queued", "approval_required", "approved", "running"}
DIRECT_MESSAGE_EVENT_TYPE = "agent_direct_message"
NOTIFICATION_EVENT_TYPE = "agent_notification_mailbox"
TERMINAL = {"completed", "failed", "cancelled"}
_PROJECTION_CACHE: Dict[str, Any] = {"value": None, "expires_at": 0.0}
_PROJECTION_CACHE_LOCK = RLock()
PROJECTION_CACHE_TTL_SECONDS = 5


def build_organization_console_summary() -> Dict[str, Any]:
    return {
        "contract": CONTRACT,
        "status": "available",
        "authority": "projection-only",
        "founder_authentication_required": True,
        "canonical_route": "/mission-control/organisation/query",
        "legacy_route_compatible": True,
        "mutation": "governed-repository-change-only",
    }


def build_internal_organisation_context() -> Dict[str, Any]:
    """Read-only context for the already-authenticated Board Room pipeline."""
    workers = _workers()
    return {
        "contract": CONTRACT,
        "status": "ready",
        "worker_count": len(workers),
        "workers": [
            {
                "agent_id": worker["agent_id"],
                "display_name": worker["display_name"],
                "role_title": worker["role_title"],
                "department_id": worker["department_id"],
                "runtime_status": worker["runtime_status"],
                "active_jobs": worker["workload"]["active_jobs"],
                "blocked_jobs": worker["workload"]["blocked_jobs"],
                "capabilities": worker["capabilities"],
                "skill_source": worker["skills"]["source"],
            }
            for worker in workers
        ],
        "authority": "organisation-console-projection",
        "mutation_enabled": False,
    }


def query_organisation(payload: Dict[str, Any]) -> Dict[str, Any]:
    denied = _authorise(payload)
    if denied:
        return denied
    if payload.get("refresh"):
        _invalidate_projection_cache()
    cached = _cached_projection()
    if cached:
        return cached
    workers = _workers()
    departments = _departments(workers)
    result = {
        "contract": CONTRACT,
        "status": "ready",
        "checked_at": _now(),
        "authority": {
            "identity": "agent-registry",
            "runtime_contract": "agent-manifest-registry",
            "structure": ["organization-registry", "management-registry"],
            "work": ["PlatformAgentTask", "PlatformWorkflowRun", "PlatformWorkflowStepRun"],
            "contributions": ["DeliveryLineage", "ArchitectureKnowledgeGraph", "PlatformExecutionEvidence"],
            "deployment": ["PlatformExecutionEvidence", "PlatformOperationalEvidence"],
            "skills": "repository-backed-operational-skills",
            "governance": "governance-authorization",
        },
        "executive": _jarvis(workers),
        "departments": departments,
        "workers": workers,
        "metrics": {
            "worker_count": len(workers),
            "department_count": len(departments),
            "active_job_count": sum(worker["workload"]["active_jobs"] for worker in workers),
            "blocked_job_count": sum(worker["workload"]["blocked_jobs"] for worker in workers),
        },
        "data_quality": _data_quality(workers),
    }
    _store_projection_cache(result)
    return copy.deepcopy(result)


def query_worker(payload: Dict[str, Any]) -> Dict[str, Any]:
    denied = _authorise(payload)
    if denied:
        return denied
    agent_id = str(payload.get("agent_id") or "").strip()
    runtime_index = build_runtime_index()
    worker = next((item for item in _workers(runtime_index=runtime_index) if item["agent_id"] == agent_id), None)
    if not worker:
        return {"contract": CONTRACT, "status": "worker-not-found", "agent_id": agent_id}
    worker["skills"] = _safe_skill_metadata(read_skill_document(agent_id), include_content=True)
    worker["skills"]["runtime_diagnostic"] = active_skill_diagnostic(agent_id)
    worker["evidence_summary"] = _evidence_counts(
        project_worker_evidence(agent_id, runtime_index, page=1, page_size=1)
    )
    return {"contract": CONTRACT, "status": "ready", "worker": worker, "checked_at": _now()}


def query_worker_evidence(payload: Dict[str, Any]) -> Dict[str, Any]:
    denied = _authorise(payload)
    if denied:
        return denied
    agent_id = str(payload.get("agent_id") or "").strip()
    if agent_id not in {item["agent_id"] for item in _workers()}:
        return {"contract": CONTRACT, "status": "worker-not-found", "agent_id": agent_id}
    evidence = project_worker_evidence(
        agent_id,
        build_runtime_index(),
        page=_positive_int(payload.get("page"), 1),
        page_size=_positive_int(payload.get("page_size"), 25),
    )
    return {
        "contract": CONTRACT,
        "status": "ready",
        "agent_id": agent_id,
        "evidence": evidence,
        "checked_at": _now(),
    }


def message_worker(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Send a founder message directly to one agent's real handler.

    Only agents explicitly marked conversational_dispatch_safe in the registry can be
    reached this way - workflow agents (builder, architect, managers, etc.) expect
    mission-shaped input and can have real side effects, so they are never
    reachable from this direct chat action, matching board_room's own
    conversational_agents() boundary.
    """
    founder = require_founder(payload)
    if not founder.get("authorized"):
        return {"contract": CONTRACT, "status": "unauthorised", "authenticated": False}
    agent_id = str(payload.get("agent_id") or "").strip()
    message = str(payload.get("message") or "").strip()
    if not message:
        return {"contract": CONTRACT, "status": "invalid-request", "error": "message is required", "agent_id": agent_id}
    agent = get_agent(agent_id)
    if not agent:
        return {"contract": CONTRACT, "status": "worker-not-found", "agent_id": agent_id}
    if not agent.conversational_dispatch_safe:
        return {
            "contract": CONTRACT,
            "status": "not-dispatch-safe",
            "agent_id": agent_id,
            "error": "This agent is not enabled for direct conversational messaging.",
        }
    task = {"input_payload": {"goal": message}, "description": message}
    try:
        result = agent.handler(task)
    except Exception as exc:
        result = {"success": False, "error": type(exc).__name__}
    create_platform_tables()
    with PlatformSessionLocal() as db:
        db.add(PlatformAuditEvent(
            event_type=DIRECT_MESSAGE_EVENT_TYPE,
            actor_type="founder",
            actor_id=founder.get("email") or "founder",
            status="completed" if result.get("success") else "failed",
            metadata_json=json.dumps(
                {"agent_id": agent_id, "message": message[:500], "response": str(result.get("message") or "")[:500]},
                sort_keys=True,
            ),
        ))
        db.commit()
    return {
        "contract": CONTRACT,
        "status": "ready" if result.get("success") else "agent-declined",
        "agent_id": agent_id,
        "response": result if result.get("success") else None,
        "error": None if result.get("success") else str(result.get("error") or "The agent did not return a usable response."),
    }


def notify_founder_about_worker(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Send the founder a real internal-only email about one agent's current state.

    Always uses the founder's own authenticated address as both the trigger and the
    recipient (never a third-party or public address), and always records a durable
    PlatformAuditEvent regardless of whether the send succeeds, so the mailbox tab
    never shows a notification that did not really happen and never hides one that
    was attempted but failed because SMTP is not configured.
    """
    founder = require_founder(payload)
    if not founder.get("authorized"):
        return {"contract": CONTRACT, "status": "unauthorised", "authenticated": False}
    agent_id = str(payload.get("agent_id") or "").strip()
    worker = next((item for item in _workers() if item["agent_id"] == agent_id), None)
    if not worker:
        return {"contract": CONTRACT, "status": "worker-not-found", "agent_id": agent_id}
    to_address = str(founder.get("email") or "").strip()
    subject = "Mission Control: %s status update" % worker["display_name"]
    body = (
        "Agent: %s (%s)\n"
        "Role: %s\n"
        "Runtime status: %s\n"
        "Active jobs: %d | Blocked jobs: %d\n"
        "Last activity: %s\n\n"
        "This is an internal Mission Control notification. It is not visible to anyone "
        "outside your founder account." % (
            worker["display_name"], agent_id, worker["role_title"], worker["runtime_status"],
            worker["workload"]["active_jobs"], worker["workload"]["blocked_jobs"],
            worker["last_activity"] or "No durable activity recorded.",
        )
    )
    sent = send_email(to_address, subject, body) if to_address and email_configured() else {
        "sent": False,
        "reason": "SMTP is not configured." if not email_configured() else "No founder email is available on this session.",
    }
    create_platform_tables()
    with PlatformSessionLocal() as db:
        db.add(PlatformAuditEvent(
            event_type=NOTIFICATION_EVENT_TYPE,
            actor_type="founder",
            actor_id=to_address or "founder",
            status="sent" if sent.get("sent") else "not-sent",
            metadata_json=json.dumps(
                {"agent_id": agent_id, "subject": subject, "reason": sent.get("reason")},
                sort_keys=True,
            ),
        ))
        db.commit()
    return {
        "contract": CONTRACT,
        "status": "sent" if sent.get("sent") else "not-sent",
        "agent_id": agent_id,
        "reason": sent.get("reason"),
    }


def query_worker_mailbox(payload: Dict[str, Any]) -> Dict[str, Any]:
    denied = _authorise(payload)
    if denied:
        return denied
    agent_id = str(payload.get("agent_id") or "").strip()
    create_platform_tables()
    with PlatformSessionLocal() as db:
        rows = (
            db.query(PlatformAuditEvent)
            .filter(PlatformAuditEvent.event_type == NOTIFICATION_EVENT_TYPE)
            .order_by(PlatformAuditEvent.created_at.desc())
            .limit(200)
            .all()
        )
    notifications = []
    for row in rows:
        try:
            metadata = json.loads(row.metadata_json or "{}")
        except (TypeError, ValueError):
            metadata = {}
        if metadata.get("agent_id") != agent_id:
            continue
        notifications.append({
            "status": row.status,
            "subject": metadata.get("subject"),
            "reason": metadata.get("reason"),
            "sent_to": row.actor_id,
            "occurred_at": row.created_at.isoformat() if row.created_at else None,
        })
    return {
        "contract": CONTRACT,
        "status": "ready",
        "agent_id": agent_id,
        "notifications": notifications[:20],
    }


def query_department(payload: Dict[str, Any]) -> Dict[str, Any]:
    denied = _authorise(payload)
    if denied:
        return denied
    department_id = str(payload.get("department_id") or "").strip()
    runtime_index = build_runtime_index()
    workers = _workers(runtime_index=runtime_index)
    department = next(
        (item for item in _departments(workers) if item["department_id"] == department_id),
        None,
    )
    if not department:
        return {"contract": CONTRACT, "status": "department-not-found", "department_id": department_id}
    members = [item for item in workers if item["department_id"] == department_id]
    return {
        "contract": CONTRACT,
        "status": "ready",
        "department": {
            **department,
            "workers": members,
            "reporting_lines": _reporting_lines(members),
            "current_assignments": [
                item for worker in members for item in worker["current_jobs"]
            ],
            "recent_activity": _recent_worker_activity(members),
            "workload_distribution": [
                {
                    "agent_id": worker["agent_id"],
                    "active_jobs": worker["workload"]["active_jobs"],
                    "blocked_jobs": worker["workload"]["blocked_jobs"],
                }
                for worker in members
            ],
            "governance": {
                "capability_grants_authority": False,
                "authority": "governance-authorization",
            },
        },
        "checked_at": _now(),
    }


def query_team(payload: Dict[str, Any]) -> Dict[str, Any]:
    denied = _authorise(payload)
    if denied:
        return denied
    team_id = str(payload.get("team_id") or "").strip()
    teams = all_teams()
    team = teams.get(team_id)
    if not team:
        return {"contract": CONTRACT, "status": "team-not-found", "team_id": team_id}
    runtime_index = build_runtime_index()
    workers = _workers(runtime_index=runtime_index)
    members = [item for item in workers if item["agent_id"] in team.member_agent_ids]
    dependencies = sorted({
        dependency
        for worker in members
        for dependency in _manifest_dependencies(worker["agent_id"])
        if dependency not in team.member_agent_ids
    })
    collaborating_teams = sorted({
        item.team_id for item in teams.values()
        if item.team_id != team_id
        and any(worker in item.member_agent_ids for worker in dependencies)
    })
    return {
        "contract": CONTRACT,
        "status": "ready",
        "team": {
            "team_id": team.team_id,
            "name": team.name,
            "department_id": team.department_id,
            "lead_agent_id": team.lead_agent_id,
            "purpose": list(team.responsibilities),
            "members": members,
            "role_distribution": [
                {"agent_id": item["agent_id"], "role": item["role_title"]}
                for item in members
            ],
            "specialisations": sorted({
                capability for item in members for capability in item["capabilities"]
            }),
            "current_assignments": [
                assignment for item in members for assignment in item["current_jobs"]
            ],
            "collaborating_teams": collaborating_teams,
            "dependencies": dependencies,
            "blockers": [
                assignment.get("blocker")
                for item in members for assignment in item["current_jobs"]
                if assignment.get("blocker")
            ],
            "recent_activity": _recent_worker_activity(members),
        },
        "checked_at": _now(),
    }


def preview_skill_change(payload: Dict[str, Any]) -> Dict[str, Any]:
    denied = _authorise(payload)
    if denied:
        return denied
    agent_id = str(payload.get("agent_id") or "").strip()
    content = str(payload.get("content") or "")
    current = read_skill_document(agent_id)
    validation = validate_skill_document(content)
    supplied_version = str(payload.get("expected_version") or "")
    conflict = bool(current.get("version") and supplied_version != current.get("version"))
    path = str(current.get("source") or "")
    package = None
    if validation["valid"] and not conflict and path:
        suffix = str(current.get("version") or "new")[:8]
        safe_agent = re.sub(r"[^a-z0-9-]+", "-", agent_id.lower().replace("_", "-")).strip("-")
        package = {
            "mission_id": "AFOS-017A-SKILL-%s" % agent_id.upper(),
            "title": "Update %s operational skills" % agent_id,
            "branch_name": "organisation-skill-%s-%s" % (safe_agent, suffix),
            "commit_message": "docs(skills): update %s operational skills" % agent_id,
            "pr_title": "Update %s operational skills" % agent_id,
            "pr_body": (
                "Governed Organisation Console skill update.\n\n"
                "Authority is unchanged. Runtime activation requires merge, release and verification."
            ),
            "file_changes": [{"path": path, "operation": "write", "content": content}],
            "live_execution": False,
            "approval_phrase": "",
        }
    return {
        "contract": CONTRACT,
        "status": "conflict" if conflict else ("valid" if validation["valid"] else "invalid"),
        "agent_id": agent_id,
        "validation": validation,
        "conflict": conflict,
        "expected_version": supplied_version or None,
        "active_version": current.get("version"),
        "change_summary": _change_summary(str(current.get("content") or ""), content),
        "github_execution_package": package,
        "governance": {
            "authority_changed": False,
            "founder_confirmation_required": True,
            "repository_execution_required": True,
            "runtime_activation_requires_release": True,
        },
        "skill_lifecycle": {
            "state": "Validated" if validation["valid"] and not conflict else "Draft",
            "source_version": current.get("version"),
            "proposed_version": _hash_content(content) if validation["valid"] else None,
            "runtime_activation_state": "Awaiting governed repository change",
        },
    }


def query_skill_history(payload: Dict[str, Any]) -> Dict[str, Any]:
    denied = _authorise(payload)
    if denied:
        return denied
    agent_id = str(payload.get("agent_id") or "").strip()
    try:
        history = skill_history(agent_id)
    except (ValueError, requests.RequestException):
        history = {"available": False, "items": [], "reason": "Skill history is temporarily unavailable."}
    lifecycle = _skill_lifecycle(agent_id, build_runtime_index())
    return {
        "contract": CONTRACT,
        "status": "ready",
        "agent_id": agent_id,
        "history": history,
        "lifecycle": lifecycle,
        "runtime_diagnostic": active_skill_diagnostic(agent_id),
    }


def query_skill_version(payload: Dict[str, Any]) -> Dict[str, Any]:
    denied = _authorise(payload)
    if denied:
        return denied
    agent_id = str(payload.get("agent_id") or "").strip()
    version = str(payload.get("version") or "").strip()
    try:
        document = read_skill_version(agent_id, version)
    except (ValueError, requests.RequestException):
        document = {"available": False, "reason": "Skill version is temporarily unavailable."}
    return {"contract": CONTRACT, "status": "ready", "agent_id": agent_id, "document": document}


def _skill_purpose(skill_content: Optional[str]) -> Optional[str]:
    """Extract the '## Purpose' section text from a skills.md document.

    Returns None (never invented text) when there is no skill document or no
    Purpose section, so callers can fall back to the agent's real description
    instead of a fabricated bio.
    """
    content = str(skill_content or "")
    marker = "## Purpose"
    start = content.find(marker)
    if start == -1:
        return None
    start += len(marker)
    end = content.find("\n## ", start)
    section = content[start:end if end != -1 else len(content)]
    return " ".join(section.split()).strip() or None


def _worker_bio(description: str, skill_content: Optional[str]) -> str:
    return _skill_purpose(skill_content) or description


_AVATAR_HUES = (204, 262, 168, 24, 340, 42, 292, 152)


def _worker_avatar(agent_id: str, display_name: str) -> Dict[str, Any]:
    """Deterministic, non-photographic avatar spec: initials over a hashed hue.

    No image data, no per-agent randomness across runs - the same agent_id
    always resolves to the same initials/hue so this never looks fabricated
    or inconsistent between page loads.
    """
    words = [word for word in re.split(r"[\s_-]+", display_name.strip()) if word]
    if len(words) >= 2:
        initials = (words[0][0] + words[1][0]).upper()
    elif words:
        initials = words[0][:2].upper()
    else:
        initials = "AI"
    stable_hash = int(_hash_content(agent_id)[:8], 16)
    hue = _AVATAR_HUES[stable_hash % len(_AVATAR_HUES)]
    return {"initials": initials, "hue": hue}


def _workers(runtime_index: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    definitions = {item["agent_id"]: item for item in list_agents()}
    manifests = all_manifests()
    roles = all_management_roles()
    departments = all_departments()
    teams = all_teams()
    role_by_agent = {role.agent_id: role for role in roles.values()}
    manager_for_role = {
        delegated: role.agent_id
        for role in roles.values()
        for delegated in role.delegates_to
    }
    department_by_agent: Dict[str, str] = {}
    team_by_agent: Dict[str, str] = {}
    for department in departments.values():
        department_by_agent.setdefault(department.lead_agent_id, department.department_id)
    for team in teams.values():
        for agent_id in team.member_agent_ids:
            department_by_agent.setdefault(agent_id, team.department_id)
            team_by_agent.setdefault(agent_id, team.team_id)
    runtime_index = runtime_index or build_runtime_index()
    tasks = runtime_index.get("tasks") or []
    workers = []
    for agent_id in sorted(set(definitions) | set(manifests)):
        definition = definitions.get(agent_id) or {}
        manifest = manifests.get(agent_id)
        role = role_by_agent.get(agent_id)
        agent_tasks = [item for item in tasks if task_agent_id(item) == agent_id]
        active = [item for item in agent_tasks if item.get("status") in ACTIVE]
        blocked = [item for item in active if item.get("status") == "approval_required" or item.get("error_message")]
        department_id = department_by_agent.get(agent_id) or (manifest.department if manifest else "unassigned")
        reports_to = None
        if role:
            reports_to = manager_for_role.get(role.role_id)
        elif manifest and manifest.depends_on:
            reports_to = manifest.depends_on[0]
        status = _runtime_status(active, blocked)
        skill = read_skill_document(agent_id)
        assignments = project_worker_assignments(agent_id, runtime_index)
        active_assignments = [item for item in assignments if item.get("status") in ACTIVE]
        registered_agent = get_agent(agent_id)
        display_name = definition.get("name") or agent_id.replace("_", " ").title()
        description = definition.get("description") or "Runtime manifest registered."
        worker = {
            "agent_id": agent_id,
            "display_name": display_name,
            "role_title": role.title if role else display_name,
            "description": description,
            "bio": _worker_bio(description, skill.get("content")),
            "avatar": _worker_avatar(agent_id, display_name),
            "conversational_dispatch_safe": bool(
                registered_agent and registered_agent.conversational_dispatch_safe
            ),
            "department_id": department_id,
            "team_id": team_by_agent.get(agent_id),
            "reports_to": reports_to,
            "capabilities": list(definition.get("capabilities") or (manifest.capabilities if manifest else [])),
            "runtime_status": status,
            "lifecycle_status": "active",
            "workload": {
                "active_jobs": len(active),
                "blocked_jobs": len(blocked),
                "completed_jobs": sum(item.get("status") == "completed" for item in agent_tasks),
                "progress_percentage": None,
            },
            "current_jobs": active_assignments,
            "last_activity": _last_activity(agent_tasks),
            "governance": {
                "approval_required": bool(
                    definition.get("requires_approval_for_new_tasks")
                    or (manifest.approval_required if manifest else False)
                ),
                "capability_grants_authority": False,
            },
            "skills": _safe_skill_metadata(skill),
            "evidence_counts": {},
        }
        workers.append(worker)
    return workers


def _departments(workers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    definitions = all_departments()
    teams = all_teams()
    department_ids = sorted(set(definitions) | {item["department_id"] for item in workers})
    result = []
    for department_id in department_ids:
        definition = definitions.get(department_id)
        members = [item for item in workers if item["department_id"] == department_id]
        result.append({
            "department_id": department_id,
            "name": definition.name if definition else department_id.replace("_", " ").title(),
            "purpose": list(definition.responsibilities) if definition else [],
            "head_agent_id": definition.lead_agent_id if definition else next(
                (item["agent_id"] for item in members if item["reports_to"] is None), None
            ),
            "worker_count": len(members),
            "active_job_count": sum(item["workload"]["active_jobs"] for item in members),
            "blocked_job_count": sum(item["workload"]["blocked_jobs"] for item in members),
            "available_worker_count": sum(item["runtime_status"] == "Available" for item in members),
            "active_worker_count": sum(item["runtime_status"] in {"Working", "Queued"} for item in members),
            "blocked_worker_count": sum(item["runtime_status"] == "Blocked" for item in members),
            "teams": [
                {
                    "team_id": team.team_id,
                    "name": team.name,
                    "lead_agent_id": team.lead_agent_id,
                    "member_agent_ids": list(team.member_agent_ids),
                    "responsibilities": list(team.responsibilities),
                }
                for team in teams.values() if team.department_id == department_id
            ],
        })
    return result


def _jarvis(workers: List[Dict[str, Any]]) -> Dict[str, Any]:
    executive = next((item for item in workers if item["agent_id"] == "ceo_agent"), None)
    return {
        "agent_id": "jarvis",
        "display_name": "Jarvis",
        "role_title": "Founder-facing AI operating authority",
        "avatar": _worker_avatar("jarvis", "Jarvis"),
        "runtime_status": executive["runtime_status"] if executive else "Available",
        "reports_to": "Founder",
        "coordinates_worker_id": executive["agent_id"] if executive else None,
        "synthetic_worker": False,
        "note": "Jarvis is the founder-facing orchestration surface, not a duplicate runtime worker.",
    }


def _runtime_status(active: List[Dict[str, Any]], blocked: List[Dict[str, Any]]) -> str:
    if blocked:
        return "Blocked"
    states = {item.get("status") for item in active}
    if "running" in states:
        return "Working"
    if "approval_required" in states:
        return "Waiting"
    if active:
        return "Queued"
    return "Available"


def _task_agent_id(task: Dict[str, Any]) -> Optional[str]:
    """Compatibility alias for existing Organisation projection checks."""
    return task_agent_id(task)


def _last_activity(tasks: List[Dict[str, Any]]) -> Optional[str]:
    values = [str(item.get("updated_at") or item.get("created_at") or "") for item in tasks]
    return max(values) if values else None


def _safe_skill_metadata(document: Dict[str, Any], include_content: bool = False) -> Dict[str, Any]:
    result = {
        "available": document.get("available"),
        "source": document.get("source"),
        "version": document.get("version"),
        "validation": document.get("validation"),
        "runtime_source": True,
        "loaded_at": document.get("loaded_at"),
        "release_revision": document.get("release_revision"),
        "load_result": document.get("load_result"),
    }
    if include_content:
        result["content"] = document.get("content")
    return result


def _change_summary(before: str, after: str) -> Dict[str, Any]:
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    return {
        "previous_lines": len(before_lines),
        "proposed_lines": len(after_lines),
        "lines_added": len([line for line in after_lines if line not in before_lines]),
        "lines_removed": len([line for line in before_lines if line not in after_lines]),
        "material_change": before.strip() != after.strip(),
    }


def _data_quality(workers: List[Dict[str, Any]]) -> Dict[str, Any]:
    reporting = _reporting_quality(workers)
    return {
        "classification": "partial" if reporting["issues"] else "complete",
        "unknown_department_count": sum(item["department_id"] == "unassigned" for item in workers),
        "missing_skill_count": sum(not item["skills"]["available"] for item in workers),
        **reporting,
        "progress_policy": "Unknown remains unknown; no elapsed-time progress is fabricated.",
    }


def _evidence_counts(evidence: Dict[str, Any]) -> Dict[str, int]:
    return {
        key: int((evidence.get(key) or {}).get("total") or 0)
        for key in (
            "mission_history",
            "activity",
            "lineage_contributions",
            "architecture_contributions",
            "repository_contributions",
            "deployment_contributions",
        )
    }


def _reporting_lines(workers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {"worker_id": item["agent_id"], "manager_id": item.get("reports_to")}
        for item in workers
    ]


def _recent_worker_activity(workers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    values = [
        {
            "agent_id": item["agent_id"],
            "occurred_at": item.get("last_activity"),
            "status": item.get("runtime_status"),
        }
        for item in workers if item.get("last_activity")
    ]
    return sorted(values, key=lambda item: item["occurred_at"], reverse=True)[:50]


def _manifest_dependencies(agent_id: str) -> List[str]:
    manifest = all_manifests().get(agent_id)
    return list(manifest.depends_on) if manifest else []


def _reporting_quality(workers: List[Dict[str, Any]]) -> Dict[str, Any]:
    identities = [item["agent_id"] for item in workers]
    identity_set = set(identities)
    issues = []
    if len(identities) != len(identity_set):
        issues.append({"type": "duplicate_worker_identity", "workers": identities})
    for worker in workers:
        manager = worker.get("reports_to")
        if manager and manager not in identity_set:
            issues.append({
                "type": "invalid_manager_id",
                "worker_id": worker["agent_id"],
                "manager_id": manager,
            })
        if worker["department_id"] == "unassigned":
            issues.append({"type": "missing_department", "worker_id": worker["agent_id"]})
    for worker in workers:
        seen, current = set(), worker["agent_id"]
        while current:
            if current in seen:
                issues.append({"type": "circular_reporting", "worker_id": worker["agent_id"]})
                break
            seen.add(current)
            current = next(
                (item.get("reports_to") for item in workers if item["agent_id"] == current),
                None,
            )
    teams = all_teams()
    departments = all_departments()
    for team in teams.values():
        if team.department_id not in departments:
            issues.append({"type": "orphan_team", "team_id": team.team_id})
        if team.lead_agent_id not in identity_set:
            issues.append({"type": "inactive_manager_reference", "team_id": team.team_id})
    return {"issues": issues, "issue_count": len(issues)}


def _positive_int(value: Any, default: int) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


def _hash_content(content: str) -> str:
    import hashlib
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _skill_lifecycle(agent_id: str, runtime_index: Dict[str, Any]) -> List[Dict[str, Any]]:
    mission_id = "AFOS-017A-SKILL-%s" % agent_id.upper()
    values = [{
        "state": "Active in runtime" if active_skill_diagnostic(agent_id)["load_result"] == "loaded" else "Repository version available",
        "source": "runtime-skill-diagnostic",
        **active_skill_diagnostic(agent_id),
    }]
    for item in runtime_index.get("execution_evidence") or []:
        if item.get("mission_id") != mission_id:
            continue
        artifact = item.get("artifact") or {}
        outcome = str(item.get("outcome") or "")
        state = "PR created" if artifact.get("pull_request_url") else (
            "Merged" if artifact.get("merge_commit_sha") else (
                "Released" if artifact.get("revision_name") else outcome.replace("_", " ").title()
            )
        )
        values.append({
            "state": state,
            "actor": item.get("actor"),
            "evidence_id": item.get("evidence_id"),
            "recorded_at": item.get("created_at"),
            "change_reference": artifact,
            "source": "PlatformExecutionEvidence",
        })
    return values


def _cached_projection() -> Optional[Dict[str, Any]]:
    with _PROJECTION_CACHE_LOCK:
        if _PROJECTION_CACHE["value"] is None or monotonic() >= _PROJECTION_CACHE["expires_at"]:
            return None
        return copy.deepcopy(_PROJECTION_CACHE["value"])


def _store_projection_cache(value: Dict[str, Any]) -> None:
    with _PROJECTION_CACHE_LOCK:
        _PROJECTION_CACHE["value"] = copy.deepcopy(value)
        _PROJECTION_CACHE["expires_at"] = monotonic() + PROJECTION_CACHE_TTL_SECONDS


def _invalidate_projection_cache() -> None:
    with _PROJECTION_CACHE_LOCK:
        _PROJECTION_CACHE["value"] = None
        _PROJECTION_CACHE["expires_at"] = 0.0


def _authorise(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    founder = require_founder(payload)
    if founder.get("authorized"):
        return None
    return {
        "contract": CONTRACT,
        "status": "unauthorised",
        "authenticated": False,
        "error": "Founder authentication is required for internal organisation data.",
    }


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
