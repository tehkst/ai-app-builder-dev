# Split from the legacy module to keep each Python file under 200 lines.
import json
import tempfile
from pathlib import Path
import app.platform.services.repair_executor_service as executor_service
WORKFLOW_RUN_ID = "v75-approved-repair"
NOT_NEEDED_WORKFLOW_RUN_ID = "v75-not-needed-repair"
TARGET_RELATIVE_PATH = "src/App.jsx"
ORIGINAL_CONTENT = "export default function App() { return <div>broken</div>; }\n"
REPLACEMENT_CONTENT = "export default function App() { return <div>fixed</div>; }\n"

def run_check():
    executor_service.reset_repair_execution_history_for_check()
    original_gate = executor_service.assert_repair_apply_allowed
    original_plan = executor_service.generate_repair_plan_for_workflow

    checks = {}
    samples = {}

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            sandbox_root = Path(tmpdir)
            target = sandbox_root / TARGET_RELATIVE_PATH
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(ORIGINAL_CONTENT, encoding="utf-8")

            operation = executor_service.build_replace_file_operation(
                target_relative_path=TARGET_RELATIVE_PATH,
                replacement_content=REPLACEMENT_CONTENT,
                reason="V75 smoke check approved replacement.",
            )

            executor_service.assert_repair_apply_allowed = _blocked_gate
            executor_service.generate_repair_plan_for_workflow = _planned_repair
            blocked_result = executor_service.execute_approved_repair(
                workflow_run_id=WORKFLOW_RUN_ID,
                sandbox_root=str(sandbox_root),
                operations=[operation],
                requested_by="smoke_check",
            )
            checks["unapproved_execution_blocked"] = blocked_result.get("blocked") is True and blocked_result.get("applied") is False
            checks["unapproved_did_not_change_file"] = target.read_text(encoding="utf-8") == ORIGINAL_CONTENT
            checks["unapproved_safe"] = _safe(blocked_result, applied_expected=False)

            executor_service.assert_repair_apply_allowed = _approved_gate
            executor_service.generate_repair_plan_for_workflow = _planned_repair
            applied_result = executor_service.execute_approved_repair(
                workflow_run_id=WORKFLOW_RUN_ID,
                sandbox_root=str(sandbox_root),
                operations=[operation],
                requested_by="smoke_check",
            )
            applied_operation = (applied_result.get("operations") or [{}])[0]
            checks["approved_execution_applied"] = applied_result.get("applied") is True and applied_result.get("blocked") is False
            checks["approved_replaced_file"] = target.read_text(encoding="utf-8") == REPLACEMENT_CONTENT
            checks["metadata_recorded"] = bool(applied_operation.get("before_sha256")) and bool(applied_operation.get("after_sha256"))
            checks["size_metadata_recorded"] = applied_operation.get("before_size_bytes") > 0 and applied_operation.get("after_size_bytes") > 0
            checks["history_recorded"] = len(applied_result.get("history") or []) == 1
            checks["approved_safe"] = _safe(applied_result, applied_expected=True)

            unsupported_result = executor_service.execute_approved_repair(
                workflow_run_id=WORKFLOW_RUN_ID,
                sandbox_root=str(sandbox_root),
                operations=[{"operation": "run_shell_command"}],
                requested_by="smoke_check",
            )
            checks["unsupported_operation_blocked"] = unsupported_result.get("blocked") is True and unsupported_result.get("applied") is False
            checks["unsupported_safe"] = _safe(unsupported_result, applied_expected=False)

            traversal_operation = executor_service.build_replace_file_operation(
                target_relative_path="../escape.txt",
                replacement_content="escape",
                reason="Should be blocked.",
            )
            traversal_result = executor_service.execute_approved_repair(
                workflow_run_id=WORKFLOW_RUN_ID,
                sandbox_root=str(sandbox_root),
                operations=[traversal_operation],
                requested_by="smoke_check",
            )
            checks["path_traversal_blocked"] = traversal_result.get("blocked") is True and traversal_result.get("applied") is False
            checks["path_traversal_safe"] = _safe(traversal_result, applied_expected=False)

            wrong_target_operation = executor_service.build_replace_file_operation(
                target_relative_path="src/Other.jsx",
                replacement_content="other",
                reason="Should be blocked by approved target list.",
            )
            wrong_target_result = executor_service.execute_approved_repair(
                workflow_run_id=WORKFLOW_RUN_ID,
                sandbox_root=str(sandbox_root),
                operations=[wrong_target_operation],
                requested_by="smoke_check",
            )
            checks["non_candidate_target_blocked"] = wrong_target_result.get("blocked") is True and wrong_target_result.get("applied") is False
            checks["non_candidate_target_safe"] = _safe(wrong_target_result, applied_expected=False)

            executor_service.generate_repair_plan_for_workflow = _not_needed_repair
            not_needed_result = executor_service.execute_approved_repair(
                workflow_run_id=NOT_NEEDED_WORKFLOW_RUN_ID,
                sandbox_root=str(sandbox_root),
                operations=[operation],
                requested_by="smoke_check",
            )
            checks["not_needed_plan_blocked"] = not_needed_result.get("blocked") is True and not_needed_result.get("applied") is False
            checks["not_needed_safe"] = _safe(not_needed_result, applied_expected=False)

            history_result = executor_service.get_repair_execution_history(WORKFLOW_RUN_ID)
            checks["history_lookup_safe"] = _safe(history_result, applied_expected=False)
            checks["history_lookup_has_record"] = len(history_result.get("history") or []) == 1

            samples = {
                "blocked_result": blocked_result,
                "applied_result": applied_result,
                "unsupported_result": unsupported_result,
                "traversal_result": traversal_result,
                "wrong_target_result": wrong_target_result,
                "not_needed_result": not_needed_result,
                "history_result": history_result,
            }
    finally:
        executor_service.assert_repair_apply_allowed = original_gate
        executor_service.generate_repair_plan_for_workflow = original_plan
        executor_service.reset_repair_execution_history_for_check()

    return {
        "check": "repair_executor_check",
        "passed": all(checks.values()),
        "checks": checks,
        "sample": samples,
    }

if __name__ == "__main__":
    result = run_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)
