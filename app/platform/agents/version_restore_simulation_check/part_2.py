# Split from the legacy module to keep each Python file under 200 lines.
from __future__ import annotations
import json
from typing import Any, Dict, List
from fastapi.testclient import TestClient
from app.main import app
from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformGeneratedFile, utc_now
from app.platform.services.generated_file_persistence_service import (
    persist_generated_files_for_workflow,
)
from app.platform.services.generated_file_version_service import (
    create_generated_file_version_snapshot,
)
from app.platform.services.workflow_run_persistence_service import get_workflow_run_detail

def _simulate_restore(client: TestClient, target_version_id: str) -> Dict[str, Any]:
    response = client.get(
        f"/platform/app-build/generated-file-versions/{target_version_id}/restore-simulation"
    )
    data = response.json()
    simulation = data.get("simulation") or {}
    impact = simulation.get("impact_report") or {}
    checks = simulation.get("validation_checks") or []

    required_safety = (
        data.get("restore_execution_performed") is False
        and data.get("db_content_mutation_performed") is False
        and data.get("disk_write_performed") is False
        and data.get("generated_code_execution_performed") is False
    )

    return {
        "name": "restore_simulation_created_without_execution",
        "passed": (
            response.status_code == 200
            and data.get("success") is True
            and data.get("found") is True
            and data.get("simulation_mode") == "dry_run_only"
            and simulation.get("simulation_mode") == "dry_run_only"
            and simulation.get("would_restore") is True
            and simulation.get("would_change_content") is True
            and simulation.get("would_change_hash") is True
            and bool(impact.get("path"))
            and bool(checks)
            and required_safety
        ),
        "status_code": response.status_code,
        "simulation_mode": data.get("simulation_mode"),
        "would_restore": simulation.get("would_restore"),
        "would_change_content": simulation.get("would_change_content"),
        "would_change_hash": simulation.get("would_change_hash"),
        "risk_level": simulation.get("risk_level"),
        "restore_execution_performed": data.get("restore_execution_performed"),
        "db_content_mutation_performed": data.get("db_content_mutation_performed"),
        "disk_write_performed": data.get("disk_write_performed"),
        "generated_code_execution_performed": data.get(
            "generated_code_execution_performed"
        ),
    }

def run_check() -> Dict[str, Any]:
    create_platform_tables()
    app.dependency_overrides[require_platform_admin] = lambda: True
    client = TestClient(app)

    checks: List[Dict[str, Any]] = []

    dashboard_check = _check_dashboard_html(client)
    checks.append(dashboard_check)

    target_check = _create_target_version(client)
    checks.append(target_check)

    target_version_id = target_check.get("first_version_id")
    if not target_version_id:
        return {
            "success": False,
            "passed": False,
            "checks": checks,
        }

    simulation_check = _simulate_restore(client, target_version_id)
    checks.append(simulation_check)

    passed = all(check.get("passed") for check in checks)

    return {
        "success": passed,
        "passed": passed,
        "workflow_run_id": target_check.get("workflow_run_id"),
        "first_generated_file_id": target_check.get("first_generated_file_id"),
        "first_version_id": target_version_id,
        "checks": checks,
    }

if __name__ == "__main__":
    print(json.dumps(run_check(), indent=2, sort_keys=True))
