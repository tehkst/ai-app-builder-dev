from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class HealthSignal:
    signal_id: str
    service: str
    status: str
    message: str


@dataclass(frozen=True)
class QueueJob:
    job_id: str
    queue: str
    status: str
    attempts: int


@dataclass(frozen=True)
class LogEntry:
    log_id: str
    service: str
    level: str
    message: str


@dataclass(frozen=True)
class MetricPoint:
    metric_id: str
    name: str
    value: float
    unit: str


@dataclass(frozen=True)
class BackupRecord:
    backup_id: str
    target: str
    status: str
    size_mb: int


@dataclass(frozen=True)
class OpsCenterSummary:
    healthy_count: int
    degraded_count: int
    queued_count: int
    error_log_count: int
    metric_count: int
    backup_count: int
    successful_backup_count: int


@dataclass(frozen=True)
class OpsCenterContext:
    health: List[HealthSignal]
    jobs: List[QueueJob]
    logs: List[LogEntry]
    metrics: List[MetricPoint]
    backups: List[BackupRecord]
    metadata: Dict[str, object]
