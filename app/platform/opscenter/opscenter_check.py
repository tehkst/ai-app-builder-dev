from __future__ import annotations

from app.platform.opscenter.opscenter_flow import run_demo_opscenter
from app.platform.opscenter.opscenter_store import (
    degraded_signals,
    error_logs,
    failed_jobs,
    healthy_signals,
    metric_by_name,
    queued_jobs,
    successful_backups,
    summarize_opscenter,
)


def main() -> None:
    data = run_demo_opscenter()
    assert len(data.health) == 3, data
    assert len(data.jobs) == 3, data
    assert len(data.logs) == 3, data
    assert len(data.metrics) == 3, data
    assert len(data.backups) == 3, data

    assert len(healthy_signals(data.health)) == 2
    assert len(degraded_signals(data.health)) == 1
    assert len(queued_jobs(data.jobs)) == 1
    assert len(failed_jobs(data.jobs)) == 1
    assert len(error_logs(data.logs)) == 1
    assert metric_by_name(data.metrics, "latency_p95")[0].value == 420
    assert len(successful_backups(data.backups)) == 2

    summary = summarize_opscenter(data.health, data.jobs, data.logs, data.metrics, data.backups)
    assert summary.healthy_count == 2, summary
    assert summary.degraded_count == 1, summary
    assert summary.queued_count == 1, summary
    assert summary.error_log_count == 1, summary
    assert summary.metric_count == 3, summary
    assert summary.backup_count == 3, summary
    assert summary.successful_backup_count == 2, summary

    print("OPSCENTER PACK CHECK PASSED")


if __name__ == "__main__":
    main()
