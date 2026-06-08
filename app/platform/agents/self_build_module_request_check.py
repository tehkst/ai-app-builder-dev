import json

import app.platform.services.self_build_module_request_service as request_service


WORKFLOW_RUN_ID = "v78-linked-workflow"


def _fake_self_healing_loop(workflow_run_id):
    return {
        "success": True,
        "workflow_run_id": workflow_run_id,
        "safety_mode": "self_healing_loop_coordinator_v77_approval_preserving",
        "loop_status": "waiting_for_repair_approval",
        "next_required_action": "approve_or_reject_repair_plan",
        "summary": "Repair plan exists but has not been approved.",
        "safety_flags": {
            "approval_gates_preserved": True,
            "auto_approval_performed": False,
            "repair_applied_by_loop": False,
            "restore_executed": False,
            "module_rollout_performed": False,
            "install_packages_performed": False,
        },
    }


def _safe(result, *, handoff_checked_expected):
    flags = result.get("safety_flags") or {}
    return (
        flags.get("self_build_module_request_checked") is True
        and flags.get("request_tracking_only") is True
        and flags.get("handoff_checked") is handoff_checked_expected
        and flags.get("workflow_created_by_request_service") is False
        and flags.get("generated_files_written") is False
        and flags.get("filesystem_write_performed") is False
        and flags.get("disk_write_performed") is False
        and flags.get("generated_code_execution_performed") is False
        and flags.get("runtime_server_started") is False
        and flags.get("install_packages_performed") is False
        and flags.get("auto_approval_performed") is False
        and flags.get("repair_applied") is False
        and flags.get("unapproved_repair_applied") is False
        and flags.get("restore_executed") is False
        and flags.get("module_rollout_performed") is False
    )


def run_check():
    request_service.reset_self_build_module_requests_for_check()
    original_inspect = request_service.inspect_self_healing_loop
    request_service.inspect_self_healing_loop = _fake_self_healing_loop

    checks = {}
    samples = {}

    try:
        created = request_service.create_self_build_module_request(
            module_name="   Internal Approval Checklist   ",
            module_goal=" Build a small dashboard panel to show pending approvals. ",
            requested_by="smoke_check",
            acceptance_criteria=[
                " Shows request list ",
                "Requires admin access",
                "",
                "No rollout until approved",
            ],
            notes="Request tracking only.",
        )
        request_record = created.get("request") or {}
        request_id = request_record.get("request_id")

        checks["create_success"] = created.get("success") is True and bool(request_id)
        checks["create_safe"] = _safe(created, handoff_checked_expected=False)
        checks["module_name_normalized"] = request_record.get("module_name") == "Internal Approval Checklist"
        checks["module_goal_normalized"] = request_record.get("module_goal") == "Build a small dashboard panel to show pending approvals."
        checks["criteria_normalized"] = request_record.get("acceptance_criteria") == [
            "Shows request list",
            "Requires admin access",
            "No rollout until approved",
        ]
        checks["starts_waiting_for_workflow"] = request_record.get("handoff_status") == "waiting_for_app_build_workflow"
        checks["created_history_recorded"] = [event.get("action") for event in created.get("history") or []] == ["created"]

        listed = request_service.list_self_build_module_requests()
        checks["list_has_request"] = listed.get("count") == 1 and (listed.get("requests") or [])[0].get("request_id") == request_id
        checks["list_safe"] = _safe(listed, handoff_checked_expected=False)

        fetched = request_service.get_self_build_module_request(request_id)
        checks["get_has_request"] = (fetched.get("request") or {}).get("request_id") == request_id
        checks["get_safe"] = _safe(fetched, handoff_checked_expected=False)

        missing = request_service.get_self_build_module_request("missing-request")
        checks["missing_lookup_safe_not_found"] = missing.get("status") == "not_found" and missing.get("request") is None

        linked = request_service.link_self_build_module_request_to_workflow(
            request_id=request_id,
            workflow_run_id=WORKFLOW_RUN_ID,
            linked_by="smoke_check",
        )
        linked_record = linked.get("request") or {}
        checks["link_success"] = linked_record.get("workflow_run_id") == WORKFLOW_RUN_ID
        checks["link_status"] = linked_record.get("status") == "linked_to_workflow"
        checks["link_handoff_status"] = linked_record.get("handoff_status") == "linked_to_existing_workflow"
        checks["link_safe"] = _safe(linked, handoff_checked_expected=False)
        checks["link_history_recorded"] = [event.get("action") for event in linked.get("history") or []] == ["created", "linked_to_workflow"]

        handoff = request_service.inspect_self_build_module_request_handoff(request_id)
        handoff_record = handoff.get("request") or {}
        loop = handoff.get("self_healing_loop") or {}
        checks["handoff_calls_v77_loop"] = loop.get("workflow_run_id") == WORKFLOW_RUN_ID
        checks["handoff_status_copied_from_loop"] = handoff_record.get("handoff_status") == "waiting_for_repair_approval"
        checks["handoff_safe"] = _safe(handoff, handoff_checked_expected=True)
        checks["handoff_history_recorded"] = [event.get("action") for event in handoff.get("history") or []] == [
            "created",
            "linked_to_workflow",
            "handoff_checked",
        ]

        no_handoff_created = request_service.create_self_build_module_request(
            module_name="Unlinked Module",
            module_goal="Request without workflow",
        )
        no_handoff_id = (no_handoff_created.get("request") or {}).get("request_id")
        no_handoff = request_service.inspect_self_build_module_request_handoff(no_handoff_id)
        checks["unlinked_handoff_no_loop"] = no_handoff.get("self_healing_loop") is None
        checks["unlinked_handoff_safe"] = _safe(no_handoff, handoff_checked_expected=False)

        samples = {
            "created": created,
            "listed": listed,
            "fetched": fetched,
            "linked": linked,
            "handoff": handoff,
            "unlinked_handoff": no_handoff,
        }
    finally:
        request_service.inspect_self_healing_loop = original_inspect
        request_service.reset_self_build_module_requests_for_check()

    return {
        "check": "self_build_module_request_check",
        "passed": all(checks.values()),
        "checks": checks,
        "sample": samples,
    }


if __name__ == "__main__":
    result = run_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)
