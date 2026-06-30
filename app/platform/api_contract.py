from __future__ import annotations

from app.platform.server import app

EXPECTED_ENDPOINTS = {
    "/",
    "/health",
    "/ready",
    "/ui",
    "/mission-control",
    "/mission-control/summary",
    "/mission-control/health",
    "/mission-control/version",
    "/mission-control/ui",
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
