from __future__ import annotations

from app.platform.opscenter.opscenter_models import BackupRecord, HealthSignal, LogEntry, MetricPoint, OpsCenterContext, QueueJob


def run_demo_opscenter() -> OpsCenterContext:
    health = [
        HealthSignal("health_api", "api", "healthy", "API responding."),
        HealthSignal("health_worker", "worker", "healthy", "Worker processing jobs."),
        HealthSignal("health_search", "search", "degraded", "Search latency elevated."),
    ]
    jobs = [
        QueueJob("job1", "generation", "queued", 0),
        QueueJob("job2", "deployment", "running", 1),
        QueueJob("job3", "billing", "failed", 3),
    ]
    logs = [
        LogEntry("log1", "api", "info", "Request completed."),
        LogEntry("log2", "worker", "error", "Job retry scheduled."),
        LogEntry("log3", "search", "warning", "Latency threshold exceeded."),
    ]
    metrics = [
        MetricPoint("metric1", "request_count", 1200, "count"),
        MetricPoint("metric2", "error_rate", 0.02, "ratio"),
        MetricPoint("metric3", "latency_p95", 420, "ms"),
    ]
    backups = [
        BackupRecord("backup1", "database", "completed", 512),
        BackupRecord("backup2", "artifacts", "completed", 2048),
        BackupRecord("backup3", "logs", "failed", 128),
    ]
    return OpsCenterContext(
        health=health,
        jobs=jobs,
        logs=logs,
        metrics=metrics,
        backups=backups,
        metadata={"flow": "opscenter_pack"},
    )
