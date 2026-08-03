from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, Optional

from app.platform.agents.app_build_request_run_check import resume_app_build_request, run_app_build_request
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.services.approval_service import decide_approval
from app.platform.services.customer_app_scope_service import draft_customer_app_scope
from app.platform.services.scoping_persistence_service import approve_scoping_record, persist_scoping_analysis
from app.platform.services.workflow_run_persistence_service import get_workflow_run_detail
from app.platform.services.workflow_step_approval_service import get_step_approval_request

# A real, previously-reproduced escalation trigger (see this feature's own task
# description) - a video app that downloads and republishes third-party content
# with no rights clearance and no monetization model. Real DeepSeek calls, not a
# script written to force a specific answer - the CEO agent decides for itself.
RISKY_APP_REQUEST = (
    "Build me a SaaS tool that downloads other creators' YouTube videos, transcribes "
    "them automatically, rewrites the transcript into a new script using AI, and "
    "republishes the rewritten video under a new title. There is no plan to license "
    "or clear rights with the original creators, and no monetization model yet - just "
    "get it live as fast as possible."
)

MAX_BUILD_ATTEMPTS = 3


def _prepare_approved_scope(app_request: str, requested_by: str) -> str:
    db = PlatformSessionLocal()
    try:
        draft = draft_customer_app_scope(app_request)
        assert draft.get("success"), draft
        record = persist_scoping_analysis(
            db,
            result=draft,
            llm_result={"status": "not_applicable"},
            requested_by=requested_by,
            request_kind="customer_app",
        )
        scoping_request_id = record["scoping_request_id"]
        approved = approve_scoping_record(db, scoping_request_id=scoping_request_id, approved_by=requested_by)
        assert approved is not None and approved.get("approval_status") == "scope_approved", approved
        return scoping_request_id
    finally:
        db.close()


def _run_real_build_until_escalated(app_request: str, requested_by: str) -> Dict[str, Any]:
    """Real DeepSeek calls all the way through - no mocking of invoke_provider.

    A real LLM's decision is not perfectly deterministic run to run, so this
    retries a bounded number of times if a given attempt happens to approve
    outright; the point is proving the real, reproduced escalation case this
    feature exists for is now handled correctly, not scripting the model's
    answer. Each attempt uses an independent scoping request/build - it is not
    the same run retried, since a real approve on attempt 1 is itself a valid,
    real outcome, just not the one this check needs to exercise.
    """
    last_result: Optional[Dict[str, Any]] = None
    for attempt in range(1, MAX_BUILD_ATTEMPTS + 1):
        scoping_request_id = _prepare_approved_scope(app_request, requested_by=f"{requested_by}-{attempt}")
        result = run_app_build_request(
            app_request=app_request,
            scoping_request_id=scoping_request_id,
            real_bridge=True,
        )
        last_result = result
        status = result.get("execution", {}).get("status")
        print("attempt %d: workflow status=%s" % (attempt, status), file=sys.stderr)
        if status == "escalated":
            return result
    raise AssertionError(
        "real CEO review did not escalate in %d attempts for a request with a real, "
        "previously-reproduced escalation trigger - last result: %s"
        % (MAX_BUILD_ATTEMPTS, json.dumps(last_result, default=str)[:2000])
    )


def _escalated_step(result: Dict[str, Any]) -> Dict[str, Any]:
    steps = result["execution"]["step_runs"]
    escalated = [step for step in steps if step.get("status") == "escalated"]
    assert len(escalated) == 1, ("expected exactly one escalated step", steps)
    return escalated[0]


def _decide_approval_for_step(step: Dict[str, Any], *, action: str, note: Optional[str], approver_id: str) -> None:
    """Mirrors exactly what the real /steps/{step_run_id}/decision/stream route does
    before it calls resume_app_build_request - decide_approval is the founder's real
    decision on the PlatformApprovalRequest record, not something resume implies."""
    db = PlatformSessionLocal()
    try:
        approval = get_step_approval_request(db, step_run_id=step["step_run_id"])
        assert approval is not None, step
        decide_approval(
            db,
            approval_id=approval["approval_id"],
            new_status="approved" if action == "approve" else "rejected",
            approver_id=approver_id,
            decision_note=note,
        )
    finally:
        db.close()


def check_escalation_creates_real_approval_request() -> None:
    result = _run_real_build_until_escalated(RISKY_APP_REQUEST, requested_by="escalation-approve-flow")
    step = _escalated_step(result)
    handler_result = step["error"]["bridge_result"]["handler_result"]
    assert handler_result["decision"] in {"escalate", "redirect"}, handler_result
    assert handler_result.get("rationale"), handler_result

    approval_id = step.get("approval_id")
    assert approval_id, step

    db = PlatformSessionLocal()
    try:
        approval = get_step_approval_request(db, step_run_id=step["step_run_id"])
    finally:
        db.close()
    assert approval is not None and approval["status"] == "pending", approval
    assert approval["source_type"] == "workflow_step", approval
    assert approval["action_payload"]["step_id"] == step["step_id"], approval
    print("Real approval request created: %s" % approval["approval_id"], file=sys.stderr)
    print("Real rationale: %s" % handler_result.get("rationale"), file=sys.stderr)


def check_approve_resumes_not_restarts() -> None:
    result = _run_real_build_until_escalated(RISKY_APP_REQUEST, requested_by="escalation-approve-resume")
    step = _escalated_step(result)
    workflow_run_id = result["execution"]["workflow_run_id"]
    scoping_request_id = result["scoping_request_id"]
    app_request = result["app_request"]
    pre_resume_completed = result["execution"]["completed_step_count"]

    db = PlatformSessionLocal()
    try:
        before = get_workflow_run_detail(db, workflow_run_id=workflow_run_id)
    finally:
        db.close()
    completed_step_run_ids_before = {
        s["step_run_id"] for s in before["steps"] if s["status"] == "completed"
    }

    _decide_approval_for_step(
        step, action="approve", note="Reviewed - acceptable risk for now.", approver_id="escalation-approve-resume",
    )
    resumed = resume_app_build_request(
        app_request=app_request,
        scoping_request_id=scoping_request_id,
        workflow_run_id=workflow_run_id,
        decision={"step_id": step["step_id"], "action": "approve", "note": "Reviewed - acceptable risk for now."},
        real_bridge=True,
    )
    assert resumed["execution"]["workflow_run_id"] == workflow_run_id, "resume must reuse the same workflow_run_id, not start a new one"
    assert resumed["execution"]["completed_step_count"] > pre_resume_completed, (
        "resume must make real forward progress on the remaining steps, not just re-mark the same one", resumed,
    )

    db = PlatformSessionLocal()
    try:
        after = get_workflow_run_detail(db, workflow_run_id=workflow_run_id)
        approval = get_step_approval_request(db, step_run_id=step["step_run_id"])
    finally:
        db.close()
    for step_run_id in completed_step_run_ids_before:
        after_step = next(s for s in after["steps"] if s["step_run_id"] == step_run_id)
        assert after_step["status"] == "completed", (
            "a step already completed before resume must not be re-run - its step_run_id "
            "must be unchanged and its status must remain completed", after_step,
        )
    decided_step = next(s for s in after["steps"] if s["step_id"] == step["step_id"])
    assert decided_step["status"] == "completed", decided_step
    assert approval is not None and approval["status"] == "approved", approval
    print(
        "Resume confirmed: same workflow_run_id=%s, completed_step_count %d -> %d"
        % (workflow_run_id, pre_resume_completed, resumed["execution"]["completed_step_count"]),
        file=sys.stderr,
    )


def check_reject_ends_the_build() -> None:
    result = _run_real_build_until_escalated(RISKY_APP_REQUEST, requested_by="escalation-reject-flow")
    step = _escalated_step(result)
    workflow_run_id = result["execution"]["workflow_run_id"]
    scoping_request_id = result["scoping_request_id"]
    app_request = result["app_request"]

    _decide_approval_for_step(
        step, action="reject", note="Not comfortable with the copyright risk.", approver_id="escalation-reject-flow",
    )
    resumed = resume_app_build_request(
        app_request=app_request,
        scoping_request_id=scoping_request_id,
        workflow_run_id=workflow_run_id,
        decision={"step_id": step["step_id"], "action": "reject", "note": "Not comfortable with the copyright risk."},
        real_bridge=True,
    )
    assert resumed["success"] is False, resumed
    # "blocked", not "failed" - the rejected step itself is "failed", but every step
    # depending on it (directly or transitively) rolls up through the same
    # dependency_failed_or_blocked path a genuine failure always has, and blocked is
    # checked ahead of failed in _workflow_status's priority. The real terminal
    # state that matters here is that it is NOT "completed" or "escalated" - the
    # build actually ended, it did not get stuck asking for another decision.
    assert resumed["execution"]["status"] in {"blocked", "failed"}, resumed["execution"]
    decided_step = next(s for s in resumed["execution"]["step_runs"] if s["step_id"] == step["step_id"])
    assert decided_step["status"] == "failed", decided_step
    assert decided_step["error"]["reason"] == "founder_rejected", decided_step

    db = PlatformSessionLocal()
    try:
        approval = get_step_approval_request(db, step_run_id=step["step_run_id"])
    finally:
        db.close()
    assert approval is not None and approval["status"] == "rejected", approval
    print("Reject confirmed: build ended in a real terminal state, not stuck.", file=sys.stderr)


def main() -> None:
    if not (os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")):
        raise SystemExit(
            "This check makes real LLM calls and requires DEEPSEEK_API_KEY (or OPENAI_API_KEY) "
            "to be set - it is intentionally not mocked."
        )
    create_platform_tables()

    check_escalation_creates_real_approval_request()
    check_approve_resumes_not_restarts()
    check_reject_ends_the_build()

    print("MANAGEMENT ESCALATION RESUME CHECK PASSED")


if __name__ == "__main__":
    main()
