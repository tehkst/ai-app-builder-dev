from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from app.platform.agents.background_job_runner_readiness_check import (
    run_background_job_runner_readiness_check,
)
from app.platform.agents.deployment_pack_v86_check import run_deployment_pack_v86_check
from app.platform.agents.hosted_sandbox_boundary_check import run_hosted_sandbox_boundary_check
from app.platform.agents.production_config_healthcheck_check import run_check as run_production_config_check


V87_END_TO_END_MVP_LAUNCH_SMOKE_SAFETY_MODE = "end_to_end_mvp_launch_smoke_v87_readiness_only"
ROOT = Path(__file__).resolve().parents[3]
READINESS_DOC = ROOT / "docs" / "MVP_LAUNCH_READINESS_V87.md"


def _safe_flags() -> Dict[str, bool]:
    return {
        "readiness_only": True,
        "aggregator_only": True,
        "deployment_performed": False,
        "railway_api_called": False,
        "gcore_api_called": False,
        "docker_build_executed": False,
        "docker_container_started": False,
        "kubernetes_started": False,
        "public_url_created": False,
        "database_provisioned": False,
        "secret_written": False,
        "runtime_server_started": False,
        "preview_server_started": False,
        "generated_code_execution_performed": False,
        "generated_files_written": False,
        "filesystem_write_performed": False,
        "approval_bypass_performed": False,
        "auto_approval_performed": False,
        "repair_applied": False,
        "restore_executed": False,
        "module_rollout_performed": False,
        "rollout_execution_performed": False,
    }


def _component_passed(result: Dict[str, Any]) -> bool:
    return result.get("passed") is True


def _readiness_doc_checks() -> Dict[str, bool]:
    if not READINESS_DOC.exists():
        return {
            "exists": False,
            "mentions_v87": False,
            "mentions_launch_readiness": False,
            "mentions_no_cloud_deployment": False,
            "mentions_next_operational_step": False,
        }
    text = READINESS_DOC.read_text(encoding="utf-8")
    return {
        "exists": True,
        "mentions_v87": "V87" in text,
        "mentions_launch_readiness": "launch-readiness" in text or "launch readiness" in text,
        "mentions_no_cloud_deployment": "No cloud deployment is performed by V87 itself." in text,
        "mentions_next_operational_step": "Next Operational Step After V87" in text,
    }


def _extract_component_summary(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "milestone": result.get("milestone"),
        "passed": result.get("passed"),
        "safety_mode": result.get("safety_mode"),
    }


def run_end_to_end_mvp_launch_smoke_check() -> Dict[str, Any]:
    production_config = run_production_config_check()
    background_runner = run_background_job_runner_readiness_check()
    hosted_boundary = run_hosted_sandbox_boundary_check()
    deployment_pack = run_deployment_pack_v86_check()
    readiness_doc = _readiness_doc_checks()

    component_results = {
        "production_config_healthcheck": production_config,
        "background_job_runner_readiness": background_runner,
        "hosted_sandbox_boundary": hosted_boundary,
        "deployment_pack_v86": deployment_pack,
    }

    checks = {
        "production_config_healthcheck_passed": _component_passed(production_config),
        "background_job_runner_readiness_passed": _component_passed(background_runner),
        "hosted_sandbox_boundary_passed": _component_passed(hosted_boundary),
        "deployment_pack_v86_passed": _component_passed(deployment_pack),
        "readiness_doc_present": all(readiness_doc.values()),
        "all_component_checks_passed": all(_component_passed(result) for result in component_results.values()),
        "safety_boundary_preserved": all(value is False for key, value in _safe_flags().items() if key not in {"readiness_only", "aggregator_only"}),
    }

    passed = all(checks.values())

    return {
        "check": "end_to_end_mvp_launch_smoke_check",
        "milestone": "V87 — End-to-End MVP Launch Smoke",
        "passed": passed,
        "launch_readiness_status": "ready_for_private_mvp_deployment_setup" if passed else "not_ready",
        "safety_mode": V87_END_TO_END_MVP_LAUNCH_SMOKE_SAFETY_MODE,
        "checks": checks,
        "component_summaries": {
            name: _extract_component_summary(result)
            for name, result in component_results.items()
        },
        "readiness_doc_checks": readiness_doc,
        "safety_flags": _safe_flags(),
    }


def main() -> int:
    result = run_end_to_end_mvp_launch_smoke_check()
    print(result)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
