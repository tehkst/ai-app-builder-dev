from __future__ import annotations


TERMINAL_STEP_STATUSES = {"completed", "failed", "blocked", "skipped"}
MAX_WORKFLOW_STEPS = 50
MAX_STEP_DEPENDENCIES = 10
# A real architect_agent architecture_plan (technology stack, full DB schema, API
# contracts, file structure) routinely runs 9-11k+ bytes once it is genuinely
# concrete - the old limits (12000/20000) were sized for the small, mostly-empty
# handler results this pipeline produced before that fix, and silently replaced
# the entire real plan with a bare {"truncated": True, "reason":
# "max_json_bytes_exceeded", ...} marker before the reviewer ever saw it - a real,
# reproduced bug (the Engineering Manager correctly reported "no usable plan to
# assess" because there genuinely wasn't one left after this guard ran).
#
# Raised again here: the redirect-regeneration fix (agent_workflow_executor_service's
# _run_step_via_bridge) makes the architect genuinely fill in gaps a reviewer flagged,
# which makes the plan *larger*, not smaller - a real regenerated plan measured 26216
# bytes on its own, already over the previous 24000-byte cap, so the fresh review after
# a real redirect saw only truncation metadata instead of the real, improved content -
# defeating the fix exactly when it worked. Raised with real headroom above that
# observed size, not just enough to barely fit it.
MAX_CONTEXT_JSON_BYTES = 45000
MAX_HANDLER_RESULT_JSON_BYTES = 36000
