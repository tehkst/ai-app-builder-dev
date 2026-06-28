from __future__ import annotations

from typing import Iterable, List, Optional

from app.platform.release.release_models import ChangeLogEntry, Release, ReleaseNote, ReleaseSummary, VersionRecord


def active_releases(releases: Iterable[Release]) -> List[Release]:
    return [release for release in releases if release.status in {"ready", "released"}]


def production_releases(releases: Iterable[Release]) -> List[Release]:
    return [release for release in releases if release.channel == "production" and release.status == "released"]


def supported_versions(versions: Iterable[VersionRecord]) -> List[VersionRecord]:
    return [version for version in versions if version.supported]


def notes_for_release(notes: Iterable[ReleaseNote], release_id: str) -> List[ReleaseNote]:
    return [note for note in notes if note.release_id == release_id]


def changes_for_release(changes: Iterable[ChangeLogEntry], release_id: str) -> List[ChangeLogEntry]:
    return [change for change in changes if change.release_id == release_id]


def find_release(releases: Iterable[Release], version: str) -> Optional[Release]:
    for release in releases:
        if release.version == version:
            return release
    return None


def summarize_release(
    releases: Iterable[Release],
    versions: Iterable[VersionRecord],
    notes: Iterable[ReleaseNote],
    changes: Iterable[ChangeLogEntry],
) -> ReleaseSummary:
    release_list = list(releases)
    return ReleaseSummary(
        release_count=len(release_list),
        active_version_count=len(supported_versions(versions)),
        note_count=len(list(notes)),
        change_count=len(list(changes)),
        production_ready_count=len(production_releases(release_list)),
    )
