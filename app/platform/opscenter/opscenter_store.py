from __future__ import annotations

from typing import Iterable, List

from app.platform.opscenter.opscenter_models import BackupRecord, HealthSignal, LogEntry, MetricPoint, OpsCenterSummary, QueueJob


def healthy_signals(signals: Iterable[HealthSignal]) -> List[HealthSignal]:
    return [signal for signal in signals if signal.status == "healthy"]


def degraded_signals(signals: Iterable[HealthSignal]) -> List[HealthSignal]:
    return [signal for signal in signals if signal.status != "healthy"]


def queued_jobs(jobs: Iterable[QueueJob]) -> List[QueueJob]:
    return [job for job in jobs if job.status == "queued"]


def failed_jobs(jobs: Iterable[QueueJob]) -> List[QueueJob]:
    return [job for job in jobs if job.status == "failed"]


def error_logs(logs: Iterable[LogEntry]) -> List[LogEntry]:
    return [log for log in logs if log.level in {"error", "critical"}]


def metric_by_name(metrics: Iterable[MetricPoint], name: str) -> List[MetricPoint]:
    return [metric for metric in metrics if metric.name == name]


def successful_backups(backups: Iterable[BackupRecord]) -> List[BackupRecord]:
    return [backup for backup in backups if backup.status == "completed"]


def summarize_opscenter(
    health: Iterable[HealthSignal],
    jobs: Iterable[QueueJob],
    logs: Iterable[LogEntry],
    metrics: Iterable[MetricPoint],
    backups: Iterable[BackupRecord],
) -> OpsCenterSummary:
    health_list = list(health)
    return OpsCenterSummary(
        healthy_count=len(healthy_signals(health_list)),
        degraded_count=len(degraded_signals(health_list)),
        queued_count=len(queued_jobs(jobs)),
        error_log_count=len(error_logs(logs)),
        metric_count=len(list(metrics)),
        backup_count=len(list(backups)),
        successful_backup_count=len(successful_backups(backups)),
    )
