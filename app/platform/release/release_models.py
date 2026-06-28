from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class Release:
    release_id: str
    version: str
    title: str
    status: str
    channel: str


@dataclass(frozen=True)
class VersionRecord:
    version_id: str
    version: str
    stability: str
    supported: bool


@dataclass(frozen=True)
class ReleaseNote:
    note_id: str
    release_id: str
    category: str
    text: str


@dataclass(frozen=True)
class ChangeLogEntry:
    change_id: str
    release_id: str
    area: str
    summary: str


@dataclass(frozen=True)
class ReleaseSummary:
    release_count: int
    active_version_count: int
    note_count: int
    change_count: int
    production_ready_count: int


@dataclass(frozen=True)
class ReleaseContext:
    releases: List[Release]
    versions: List[VersionRecord]
    notes: List[ReleaseNote]
    changes: List[ChangeLogEntry]
    metadata: Dict[str, object]
