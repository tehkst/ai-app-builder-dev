from __future__ import annotations

from app.platform.server import app

EXPECTED_ENDPOINTS = {
    "/",
    "/login",
    "/status",
    "/health",
    "/ready",
    "/ui",
    "/mission-control",
    "/mission-control/summary",
    "/mission-control/health",
    "/mission-control/version",
    "/mission-control/ui",
    "/mission-control/founder-console",
    "/mission-control/operating-console",
    "/mission-control/operating-console/dashboard",
    "/mission-control/operating-console/chat",
    "/mission-control/operating-console/workflow",
    "/mission-control/company-intelligence",
    "/mission-control/company-intelligence/snapshot",
    "/mission-control/executive-intelligence",
    "/mission-control/executive-intelligence/briefing",
    "/mission-control/auth",
    "/mission-control/auth/login",
    "/mission-control/auth/session",
    "/mission-control/auth/logout",
    "/mission-control/executive-office",
    "/mission-control/workforce",
    "/mission-control/knowledge-vault",
    "/mission-control/company-objects",
    "/mission-control/board-room",
    "/mission-control/company-brain",
    "/mission-control/company-graph",
    "/mission-control/founder",
    "/mission-control/requests",
    "/mission-control/proposals",
    "/mission-control/proposals/generate",
    "/mission-control/approvals",
    "/mission-control/proposals/{proposal_id}",
    "/mission-control/proposals/approve",
    "/mission-control/proposals/reject",
    "/mission-control/missions",
    "/mission-control/missions/{mission_id}",
    "/mission-control/missions/plan",
    "/mission-control/missions/start",
    "/mission-control/runtime",
    "/mission-control/runtime/memory",
    "/mission-control/runtime/ai-provider",
    "/mission-control/runtime/ai/invoke",
    "/mission-control/runtime/worker/next-step",
    "/mission-control/runtime/secrets",
    "/mission-control/runtime/events",
    "/mission-control/engineering-worker",
    "/mission-control/engineering-worker/blueprint",
    "/mission-control/engineering-worker/pr-plan",
    "/mission-control/repository",
    "/mission-control/repository/index",
    "/mission-control/repository/context",
    "/mission-control/repository/search",
    "/mission-control/repository/file-plan",
    "/mission-control/code",
    "/mission-control/code/status",
    "/mission-control/code/generate",
    "/mission-control/code/validate",
    "/mission-control/code/package",
    "/mission-control/patches",
    "/mission-control/patches/prepare",
    "/mission-control/patches/apply",
    "/mission-control/patches/status",
    "/mission-control/pull-requests",
    "/mission-control/pull-requests/prepare",
    "/mission-control/pull-requests/create",
    "/mission-control/pull-requests/status",
    "/mission-control/github-executor",
    "/mission-control/github-executor/plan",
    "/mission-control/github-executor/execute",
    "/mission-control/github-executor/status",
    "/mission-control/ci-repair",
    "/mission-control/ci-repair/diagnose",
    "/mission-control/ci-repair/plan",
    "/mission-control/ci-repair/retry",
    "/mission-control/ci-repair/status",
    "/mission-control/handover",
}


def registered_paths() -> set[str]:
    return {route.path for route in app.routes if hasattr(route, "path")}


def main() -> None:
    paths = registered_paths()
    missing = sorted(EXPECTED_ENDPOINTS - paths)
    assert not missing, f"Missing Mission Control API endpoints: {missing}"
    print("MISSION CONTROL API CONTRACT PASSED")


if __name__ == "__main__":
    main()
