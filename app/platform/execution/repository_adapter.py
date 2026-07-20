from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List

from app.platform.governance_authorization.service import authorize_governed_action, record_governed_outcome
from app.platform.workspaces.execution_service import acquire_workspace_lease, inspect_workspace


MUTATIONS = {"checkout", "fetch", "pull", "merge", "rebase", "reset", "cherry_pick", "revert"}
PROTECTED = {"main", "master"}


def execute_repository_action(payload: Dict[str, Any]) -> Dict[str, Any]:
    action = str(payload.get("action") or "").strip()
    workspace = inspect_workspace(str(payload.get("workspace_id") or ""))
    if workspace.get("status") == "not-found": return {"status": "blocked", "error": "Durable workspace not found."}
    owner = str(payload.get("actor") or "mission_control")
    lease = acquire_workspace_lease(workspace["workspace_id"], owner)
    if not lease.get("acquired"): return {"status": "blocked", "error": "Workspace lease is held by another execution."}

    # Coding workspace context: the agent already owns the lease, no founder
    # approval is required for read-only or workspace-internal operations.
    coding_workspace = bool(payload.get("coding_workspace") is True)

    decision = authorize_governed_action(payload, "repository_%s" % action, policy_context={
        "workspace_ownership": workspace.get("owner_id") == owner,
        "platform_state": True,
        "durable_approval_required": not coding_workspace,
        "coding_workspace": coding_workspace,
        "destructive_operation_policy": action != "reset" or payload.get("confirm_destructive") is True,
    })
    if action in MUTATIONS and not decision.get("allowed"): return {"status": "blocked", "authorization": decision, "error": decision.get("reason")}
    prepared = _ensure_repository(workspace)
    if prepared: return {"status": "failed", "error": prepared, "authorization": decision}
    args = _command(action, payload, workspace)
    if isinstance(args, str): return {"status": "blocked", "error": args}
    completed = subprocess.run(args, cwd=workspace["local_path"], text=True, capture_output=True, timeout=120)
    result = {"status": "completed" if completed.returncode == 0 else "failed", "action": action, "workspace_id": workspace["workspace_id"], "output": completed.stdout[-4000:], "error": completed.stderr[-2000:] if completed.returncode else None}
    result["governance_evidence"] = record_governed_outcome(payload, decision, result)
    return result


def repository_capability_probe() -> Dict[str, Any]:
    completed = subprocess.run(["git", "--version"], text=True, capture_output=True)
    return {"implemented": True, "configured": completed.returncode == 0, "detail": completed.stdout.strip()}


def _ensure_repository(workspace: Dict[str, Any]) -> Any:
    path = Path(workspace["local_path"])
    if (path / ".git").exists(): return None
    path.mkdir(parents=True, exist_ok=True)
    repository = str(workspace.get("repository") or "")
    url = repository if "://" in repository else "https://github.com/%s.git" % repository
    completed = subprocess.run(["git", "clone", "--no-checkout", url, str(path)], text=True, capture_output=True, timeout=120)
    return None if completed.returncode == 0 else "Workspace checkout recovery failed: %s" % completed.stderr[-1000:]


def _command(action: str, payload: Dict[str, Any], workspace: Dict[str, Any]) -> Any:
    ref = str(payload.get("ref") or "").strip()
    remote = str(payload.get("remote") or "origin").strip()
    if action == "checkout": return ["git", "checkout", ref] if ref else "ref is required."
    if action == "fetch": return ["git", "fetch", remote]
    if action == "pull": return ["git", "pull", "--ff-only", remote, ref or workspace.get("branch") or "main"]
    if action == "merge": return ["git", "merge", "--no-edit", ref] if ref else "ref is required."
    if action == "rebase": return ["git", "rebase", ref] if ref and workspace.get("branch") not in PROTECTED else "Guarded rebase requires a ref and a non-protected workspace branch."
    if action == "reset":
        if workspace.get("branch") in PROTECTED or payload.get("confirm_destructive") is not True: return "Guarded reset requires a non-protected branch and confirm_destructive=true."
        return ["git", "reset", "--hard", ref] if ref else "ref is required."
    if action == "cherry_pick": return ["git", "cherry-pick", ref] if ref else "ref is required."
    if action == "revert": return ["git", "revert", "--no-edit", ref] if ref else "ref is required."
    return "Unsupported repository action."
