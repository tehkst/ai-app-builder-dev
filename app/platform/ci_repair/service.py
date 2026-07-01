from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.platform.code_planner.service import DEFAULT_VALIDATION_GATES
from app.platform.patch_application.service import REPOSITORY_FULL_NAME


def build_ci_repair_summary() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Autonomous CI Repair Loop",
        "milestone": "GCP-16",
        "status": "ci-repair-loop-ready",
        "mode": "diagnose-plan-repair-retry",
        "purpose": "Classify CI failures, prepare repair plans, and govern retry execution for autonomous engineering pull requests.",
        "repository": REPOSITORY_FULL_NAME,
        "governance_rule": "CI repairs may update feature branches only. Merge remains blocked until CI passes and founder review is complete.",
        "endpoints": {
            "summary": "GET /mission-control/ci-repair",
            "diagnose": "POST /mission-control/ci-repair/diagnose",
            "plan": "POST /mission-control/ci-repair/plan",
            "retry": "POST /mission-control/ci-repair/retry",
            "status": "POST /mission-control/ci-repair/status",
        },
        "capabilities": [
            "ci-failure-classification",
            "log-signal-extraction",
            "repair-plan-generation",
            "retry-readiness-checks",
            "feature-branch-only-repair-contract",
        ],
        "safety": {
            "main_branch_write_allowed": False,
            "founder_approval_required_for_repair": True,
            "ci_required_before_merge": True,
            "max_repair_attempts_default": 3,
        },
        "next_step": "Use diagnose and plan after a PR Validation failure, then execute repairs through GCP-15 GitHub executor.",
    }


def diagnose_ci_failure(payload: dict[str, Any]) -> dict[str, Any]:
    diagnosed_at = _now()
    failure = _normalize_failure(payload)
    diagnosis_id = _id("CIDIAG", diagnosed_at, failure)
    signals = _extract_signals(failure["logs"])
    category = _classify_failure(signals, failure)
    return {
        "company": "AI Software Factory",
        "product": "Autonomous CI Repair Loop",
        "milestone": "GCP-16",
        "status": "ci-failure-diagnosed",
        "diagnosis_id": diagnosis_id,
        "repository": failure["repository"],
        "pr_number": failure["pr_number"],
        "workflow": failure["workflow"],
        "run_id": failure["run_id"],
        "category": category,
        "confidence": _confidence(category, signals),
        "signals": signals,
        "merge_allowed": False,
        "next_step": "POST /mission-control/ci-repair/plan to create a governed repair plan.",
    }


def plan_ci_repair(payload: dict[str, Any]) -> dict[str, Any]:
    planned_at = _now()
    failure = _normalize_failure(payload)
    signals = _extract_signals(failure["logs"])
    category = str(payload.get("category") or _classify_failure(signals, failure))
    plan_id = _id("CIREPAIR", planned_at, {"failure": failure, "category": category, "signals": signals})
    repair_steps = _repair_steps_for(category, signals)
    branch = str(payload.get("feature_branch") or payload.get("branch") or "feature/repair-ci-failure")
    return {
        "company": "AI Software Factory",
        "product": "Autonomous CI Repair Loop",
        "milestone": "GCP-16",
        "status": "ci-repair-plan-created",
        "repair_plan_id": plan_id,
        "repository": failure["repository"],
        "pr_number": failure["pr_number"],
        "workflow": failure["workflow"],
        "run_id": failure["run_id"],
        "failure_category": category,
        "target_branch": branch,
        "main_branch_write_allowed": False,
        "repair_steps": repair_steps,
        "recommended_write_batch": _recommended_write_batch(category, signals),
        "validation_gates": failure["validation_gates"],
        "approval_gate": {
            "required": True,
            "reason": "Autonomous repair updates must be approved before live GitHub execution.",
        },
        "next_step": "Approve the repair plan, then execute it through /mission-control/github-executor/execute.",
    }


def retry_ci_repair(payload: dict[str, Any]) -> dict[str, Any]:
    retry_at = _now()
    repair_plan_id = str(payload.get("repair_plan_id") or "CIREPAIR-UNSPECIFIED")
    approval = _normalize_approval(payload)
    attempts = int(payload.get("attempts") or payload.get("repair_attempts") or 0)
    max_attempts = int(payload.get("max_attempts") or 3)
    retry_id = _id("CIRETRY", retry_at, {"repair_plan_id": repair_plan_id, "attempts": attempts, "approval": approval})

    if approval["status"] != "approved":
        return {
            "company": "AI Software Factory",
            "product": "Autonomous CI Repair Loop",
            "milestone": "GCP-16",
            "status": "blocked-awaiting-founder-approval",
            "retry_id": retry_id,
            "repair_plan_id": repair_plan_id,
            "retry_started": False,
            "reason": "Founder approval is required before repair retry execution.",
        }

    if attempts >= max_attempts:
        return {
            "company": "AI Software Factory",
            "product": "Autonomous CI Repair Loop",
            "milestone": "GCP-16",
            "status": "blocked-max-repair-attempts-reached",
            "retry_id": retry_id,
            "repair_plan_id": repair_plan_id,
            "retry_started": False,
            "attempts": attempts,
            "max_attempts": max_attempts,
            "next_step": "Escalate to founder or senior engineering review.",
        }

    return {
        "company": "AI Software Factory",
        "product": "Autonomous CI Repair Loop",
        "milestone": "GCP-16",
        "status": "repair-retry-ready",
        "retry_id": retry_id,
        "repair_plan_id": repair_plan_id,
        "attempts": attempts + 1,
        "max_attempts": max_attempts,
        "retry_started": False,
        "execution_contract": {
            "executor": "GCP-15 Live GitHub REST Executor",
            "required_endpoint": "POST /mission-control/github-executor/execute",
            "required_flags": ["approval.status=approved", "live_execution=true"],
            "target": "feature-branch-only",
        },
        "next_step": "Submit the approved repair write batch to the GitHub executor, then rerun PR Validation.",
    }


def get_ci_repair_status(payload: dict[str, Any]) -> dict[str, Any]:
    ci_status = str(payload.get("ci_status") or "pending").lower().strip()
    founder_review_status = str(payload.get("founder_review_status") or "pending").lower().strip()
    merge_allowed = ci_status in {"success", "passed", "green"} and founder_review_status in {"approved", "accepted"}
    return {
        "company": "AI Software Factory",
        "product": "Autonomous CI Repair Loop",
        "milestone": "GCP-16",
        "status": "tracked",
        "repair_plan_id": str(payload.get("repair_plan_id") or "CIREPAIR-UNSPECIFIED"),
        "state": {
            "ci_status": ci_status,
            "repair_attempts": int(payload.get("repair_attempts") or 0),
            "last_failure_category": str(payload.get("last_failure_category") or "unknown"),
            "founder_review_status": founder_review_status,
            "merge_allowed": merge_allowed,
        },
        "next_step": "Merge only when CI is green and founder review is approved." if merge_allowed else "Continue repair or review workflow.",
    }


def _normalize_failure(payload: dict[str, Any]) -> dict[str, Any]:
    source = payload.get("failure") if isinstance(payload.get("failure"), dict) else payload
    logs = source.get("logs") or source.get("log_excerpt") or source.get("error") or ""
    if isinstance(logs, list):
        logs = "\n".join(str(item) for item in logs)
    return {
        "repository": str(source.get("repository") or source.get("repository_full_name") or REPOSITORY_FULL_NAME),
        "pr_number": int(source.get("pr_number") or source.get("pull_request_number") or 0),
        "workflow": str(source.get("workflow") or source.get("workflow_name") or "PR Validation"),
        "run_id": str(source.get("run_id") or source.get("workflow_run_id") or "RUN-UNSPECIFIED"),
        "job": str(source.get("job") or source.get("job_name") or "validation"),
        "logs": str(logs),
        "validation_gates": source.get("validation_gates") or DEFAULT_VALIDATION_GATES,
    }


def _extract_signals(logs: str) -> list[dict[str, str]]:
    lowered = logs.lower()
    patterns = [
        ("syntax-error", ["syntaxerror", "invalid syntax", "unexpected eof"]),
        ("import-error", ["modulenotfounderror", "importerror", "cannot import name"]),
        ("api-contract-error", ["missing mission control api endpoints", "api contract", "expected_endpoints"]),
        ("test-failure", ["assertionerror", "failed", "pytest", "test failed"]),
        ("timeout", ["timeout", "timed out", "read operation timed out"]),
        ("permission-error", ["permission denied", "403", "forbidden", "unauthorized"]),
    ]
    signals = []
    for name, needles in patterns:
        for needle in needles:
            if needle in lowered:
                signals.append({"signal": name, "matched": needle})
                break
    if not signals and logs.strip():
        signals.append({"signal": "unknown-error", "matched": logs.strip()[:80]})
    return signals


def _classify_failure(signals: list[dict[str, str]], failure: dict[str, Any]) -> str:
    signal_names = {item["signal"] for item in signals}
    if "syntax-error" in signal_names:
        return "syntax-repair"
    if "import-error" in signal_names:
        return "dependency-or-import-repair"
    if "api-contract-error" in signal_names:
        return "api-contract-repair"
    if "timeout" in signal_names:
        return "timeout-hardening"
    if "permission-error" in signal_names:
        return "permissions-or-secret-configuration"
    if "test-failure" in signal_names:
        return "test-regression-repair"
    return "general-ci-repair"


def _confidence(category: str, signals: list[dict[str, str]]) -> str:
    if category == "general-ci-repair" or not signals:
        return "low"
    if len(signals) == 1:
        return "medium"
    return "high"


def _repair_steps_for(category: str, signals: list[dict[str, str]]) -> list[str]:
    base = [
        "Read failing job logs and identify the smallest safe patch.",
        "Apply repair only to the feature branch.",
        "Run validation gates before requesting merge.",
    ]
    category_steps = {
        "syntax-repair": ["Fix malformed Python syntax or incomplete blocks."],
        "dependency-or-import-repair": ["Correct import paths, missing package references, or circular imports."],
        "api-contract-repair": ["Update server route registration or API contract endpoint list."],
        "timeout-hardening": ["Add timeout handling, retries, or graceful failure responses."],
        "permissions-or-secret-configuration": ["Verify secret names, IAM permissions, and runtime configuration."],
        "test-regression-repair": ["Adjust implementation to satisfy existing tests without weakening validation."],
        "general-ci-repair": ["Create a targeted patch after deeper log inspection."],
    }
    return category_steps.get(category, category_steps["general-ci-repair"]) + base


def _recommended_write_batch(category: str, signals: list[dict[str, str]]) -> list[dict[str, str]]:
    mapping = {
        "api-contract-repair": ["app/platform/server.py", "app/platform/api_contract.py"],
        "dependency-or-import-repair": ["app/platform/server.py"],
        "timeout-hardening": ["app/platform/runtime/ai_provider.py", "app/platform/runtime/service.py"],
        "permissions-or-secret-configuration": ["app/platform/runtime/service.py", "app/platform/github_execution/service.py"],
    }
    paths = mapping.get(category, ["app/platform/server.py"])
    return [
        {
            "path": path,
            "operation": "modify",
            "content_source": "repair-generated-patch",
            "intent": f"Apply {category} repair.",
        }
        for path in paths
    ]


def _normalize_approval(payload: dict[str, Any]) -> dict[str, str]:
    approval = payload.get("approval") if isinstance(payload.get("approval"), dict) else {}
    return {
        "status": str(approval.get("status") or payload.get("approval_status") or "pending").lower().strip(),
        "approved_by": str(approval.get("approved_by") or payload.get("approved_by") or "").strip(),
        "approval_id": str(approval.get("approval_id") or payload.get("approval_id") or "APPROVAL-UNSPECIFIED"),
    }


def _id(prefix: str, timestamp: str, data: Any) -> str:
    digest = hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:12].upper()
    return f"{prefix}-{timestamp[:10].replace('-', '')}-{digest}"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
