# Split from the legacy module to keep each Python file under 200 lines.
import json
import app.platform.services.internal_dogfooding_module_service as dogfood_service
import app.platform.services.module_rollout_gate_service as rollout_service
import app.platform.services.self_build_module_request_service as request_service
WORKFLOW_RUN_ID = "v80-dogfooding-workflow"
_LOOP_STATUS = "waiting_for_repair_approval"

if __name__ == "__main__":
    result = run_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)
