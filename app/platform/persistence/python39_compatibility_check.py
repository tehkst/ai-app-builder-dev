from __future__ import annotations

import ast
import importlib
from pathlib import Path


PRODUCTION_MODULES = (
    "app.platform.persistence.database",
    "app.platform.persistence.readiness",
    "app.platform.operating_console.mission_run_service",
    "app.platform.operating_console.mission_runtime_agent",
    "app.platform.agents.worker",
)

PR_388_FILES = (
    "app/core/database.py", "app/core/database_urls.py", "app/core/environment.py",
    "app/platform/agents/lease_safety_check.py", "app/platform/agents/specialists.py",
    "app/platform/agents/worker.py", "app/platform/api/agent_task_routes.py",
    "app/platform/architecture_agent/service.py", "app/platform/capability_intelligence/service.py",
    "app/platform/engineering/change_set_service.py", "app/platform/execution/orchestrator.py",
    "app/platform/execution/workflow_check.py", "app/platform/operating_console/action_flow_check.py",
    "app/platform/operating_console/action_service.py", "app/platform/operating_console/mission_run_service.py",
    "app/platform/operating_console/mission_runtime_agent.py", "app/platform/persistence/check.py",
    "app/platform/persistence/database.py", "app/platform/persistence/readiness.py", "app/platform/server.py",
    "app/platform/services/agent_task_service/__init__.py", "app/platform/services/agent_task_service/part_3.py",
    "app/platform/services/agent_task_service/part_4.py", "app/platform/services/agent_task_service/part_5.py",
    "app/platform/services/agent_task_service/part_6.py",
    "app/platform/services/bounded_background_job_runner_service.py",
    "app/platform/services/workflow_run_persistence_service.py", "app/platform/ui/action_progress_check.py",
    "app/platform/ui/founder_dashboard_board_chat.py",
)


def main() -> None:
    for module in PRODUCTION_MODULES:
        importlib.import_module(module)
    for filename in PR_388_FILES:
        source = Path(filename).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=filename, feature_version=(3, 9))
        postponed = source.startswith("from __future__ import annotations")
        if not postponed:
            annotations = [node.annotation for node in ast.walk(tree) if isinstance(node, (ast.AnnAssign, ast.arg)) and node.annotation]
            annotations.extend(node.returns for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.returns)
            assert not any(isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr) for annotation in annotations for node in ast.walk(annotation)), filename
    print("PR #388 Python 3.9 import compatibility check passed")


if __name__ == "__main__":
    main()
