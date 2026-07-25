from __future__ import annotations

from time import perf_counter
from unittest.mock import patch

from app.platform.organization_console.evidence import project_worker_evidence
from app.platform.organization_console.service import (
    _invalidate_projection_cache,
    query_organisation,
    query_worker,
)


def _milliseconds(started: float) -> float:
    return round((perf_counter() - started) * 1000, 2)


def main() -> None:
    with patch(
        "app.platform.organization_console.service.require_founder",
        return_value={"authorized": True},
    ):
        _invalidate_projection_cache()
        started = perf_counter()
        landing = query_organisation({"token": "founder", "refresh": True})
        cold_ms = _milliseconds(started)
        started = perf_counter()
        query_organisation({"token": "founder"})
        cached_ms = _milliseconds(started)
        started = perf_counter()
        profile = query_worker({"token": "founder", "agent_id": "architect_agent"})
        profile_ms = _milliseconds(started)

    tasks = [{
        "task_id": "TASK-%s" % index,
        "title": "Representative task %s" % index,
        "status": "completed",
        "priority": "normal",
        "assigned_agent": "architect_agent",
        "input_payload": {},
        "result_payload": {"agent_id": "architect_agent"},
        "updated_at": "2026-07-25T00:00:00+00:00",
    } for index in range(500)]
    started = perf_counter()
    evidence = project_worker_evidence(
        "architect_agent",
        {
            "tasks": tasks,
            "runs": {},
            "execution_evidence": [],
            "operational_evidence": [],
        },
        page=1,
        page_size=25,
    )
    evidence_ms = _milliseconds(started)

    assert landing["status"] == "ready", landing
    assert profile["status"] == "ready", profile
    assert evidence["mission_history"]["total"] == 500, evidence
    assert len(evidence["mission_history"]["items"]) == 25, evidence
    assert cached_ms <= cold_ms, (cold_ms, cached_ms)
    assert max(cold_ms, profile_ms, evidence_ms) < 5000, {
        "landing_cold_ms": cold_ms,
        "landing_cached_ms": cached_ms,
        "worker_profile_ms": profile_ms,
        "worker_evidence_500_tasks_ms": evidence_ms,
    }
    print({
        "landing_cold_ms": cold_ms,
        "landing_cached_ms": cached_ms,
        "worker_profile_ms": profile_ms,
        "worker_evidence_500_tasks_ms": evidence_ms,
        "directory_window_size": 100,
        "evidence_page_size": 25,
    })
    print("AFOS-017A PERFORMANCE CHECK PASSED")


if __name__ == "__main__":
    main()
