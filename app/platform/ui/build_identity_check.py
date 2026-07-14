from __future__ import annotations

from unittest.mock import patch

from app.platform.ui.dashboard_context import build_dashboard_context
from app.platform.ui.founder_dashboard_stable import render_stable_founder_dashboard


def main() -> None:
    with patch.dict("os.environ", {"PLATFORM_VERSION": "0.68.0", "ENVIRONMENT": "production", "GIT_COMMIT_SHA": "17553b88abcdef", "K_SERVICE": "ai-software-factory-production", "K_REVISION": "ai-software-factory-production-00121-2m6"}, clear=False):
        context = build_dashboard_context()
        html = render_stable_founder_dashboard()
    assert context.build_identity == "v0.68.0 · PROD · 17553b88 · 00121-2m6"
    assert "Git commit: 17553b88abcdef" in context.build_details
    assert context.build_identity in html
    assert context.build_details in html
    assert "class=\"build-id\"" in html

    missing = {"GIT_COMMIT_SHA": "", "COMMIT_SHA": "", "SOURCE_COMMIT": "", "GITHUB_SHA": "", "K_REVISION": "", "CLOUD_RUN_REVISION": ""}
    with patch.dict("os.environ", missing, clear=False):
        local = build_dashboard_context()
    assert "None" not in local.build_identity
    assert "None" not in local.build_details
    print("dashboard build identity ok")


if __name__ == "__main__":
    main()
