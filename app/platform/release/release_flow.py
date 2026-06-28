from __future__ import annotations

from app.platform.release.release_models import ChangeLogEntry, Release, ReleaseContext, ReleaseNote, VersionRecord


def run_demo_release() -> ReleaseContext:
    releases = [
        Release("release_150", "1.0.0-rc1", "Release Candidate", "ready", "staging"),
        Release("release_151", "1.0.0", "Version 1.0", "released", "production"),
        Release("release_legacy", "0.9.0", "Legacy", "archived", "production"),
    ]
    versions = [
        VersionRecord("version_100", "1.0.0", "stable", True),
        VersionRecord("version_rc", "1.0.0-rc1", "candidate", True),
        VersionRecord("version_090", "0.9.0", "legacy", False),
    ]
    notes = [
        ReleaseNote("note1", "release_151", "platform", "Version 1.0 launch baseline."),
        ReleaseNote("note2", "release_151", "saas", "Admin and portal flows included."),
        ReleaseNote("note3", "release_150", "quality", "Release candidate validation."),
    ]
    changes = [
        ChangeLogEntry("change1", "release_151", "workspace", "Workspace pack included."),
        ChangeLogEntry("change2", "release_151", "operations", "Operations center included."),
        ChangeLogEntry("change3", "release_151", "admin", "Administration pack included."),
    ]
    return ReleaseContext(
        releases=releases,
        versions=versions,
        notes=notes,
        changes=changes,
        metadata={"flow": "release_pack"},
    )
