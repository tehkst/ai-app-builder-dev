from __future__ import annotations

from unittest.mock import patch

from app.platform.release.release_flow import observe_releases
from app.platform.release.execution_adapter import _request


def main() -> None:
    observed = {"status": "completed", "action": "release_history", "result": [{"tag_name": "v1.0.0"}]}
    with patch("app.platform.release.release_flow.execute_release_action", return_value=observed):
        data = observe_releases()
    assert data.metadata["flow"] == "production_release_adapter"
    assert data.metadata["observed"] == observed
    assert data.releases == [] and data.versions == []
    assert _request("create_release", {"tag_name": "v1.0.0"})[1] == "/releases"
    assert _request("version_tag", {"tag_name": "v1.0.0", "commit_sha": "abc"})[1] == "/git/refs"
    assert _request("compare_releases", {"base": "v0.9.0", "head": "v1.0.0"})[1] == "/compare/v0.9.0...v1.0.0"
    print("PRODUCTION RELEASE ADAPTER CHECK PASSED")


if __name__ == "__main__":
    main()
