from __future__ import annotations

from app.platform.release.release_flow import run_demo_release
from app.platform.release.release_store import (
    active_releases,
    changes_for_release,
    find_release,
    notes_for_release,
    production_releases,
    summarize_release,
    supported_versions,
)


def main() -> None:
    data = run_demo_release()
    assert len(data.releases) == 3, data
    assert len(data.versions) == 3, data
    assert len(data.notes) == 3, data
    assert len(data.changes) == 3, data

    assert len(active_releases(data.releases)) == 2
    assert len(production_releases(data.releases)) == 1
    assert len(supported_versions(data.versions)) == 2
    assert len(notes_for_release(data.notes, "release_151")) == 2
    assert len(changes_for_release(data.changes, "release_151")) == 3

    release = find_release(data.releases, "1.0.0")
    assert release is not None
    assert release.status == "released"

    summary = summarize_release(data.releases, data.versions, data.notes, data.changes)
    assert summary.release_count == 3, summary
    assert summary.active_version_count == 2, summary
    assert summary.note_count == 3, summary
    assert summary.change_count == 3, summary
    assert summary.production_ready_count == 1, summary

    print("RELEASE PACK CHECK PASSED")


if __name__ == "__main__":
    main()
