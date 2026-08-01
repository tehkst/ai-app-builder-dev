from __future__ import annotations

from app.platform.gcp.environment_topology import ENVIRONMENTS
from app.platform.architecture_knowledge_graph.infrastructure_projection import project_infrastructure


def main() -> None:
    # Unlike every other app/platform/gcp/*.py check, this one is allowed to need live
    # GCP credentials - it exists specifically to compare declared topology
    # (environment_topology.py) against what's actually deployed, right before a real
    # promotion. It must still degrade rather than crash when credentials genuinely
    # aren't available (e.g. run by accident outside CI), the same as
    # infrastructure_projection.py's own projections do.
    result = project_infrastructure(refresh=True)
    drift = result.get("drift", {})

    unavailable = [name for name in ENVIRONMENTS if drift.get(name, {}).get("status") == "unavailable"]
    if len(unavailable) == len(ENVIRONMENTS):
        print("INFRASTRUCTURE DRIFT CHECK SKIPPED: no environment was observable (no gcloud credentials?)")
        return

    failures = []
    for name in ENVIRONMENTS:
        entry = drift.get(name, {})
        if entry.get("status") == "drift":
            for issue in entry.get("issues", []):
                failures.append("%s: %s" % (name, issue))

    if failures:
        for failure in failures:
            print("DRIFT: %s" % failure)
        raise SystemExit("INFRASTRUCTURE DRIFT CHECK FAILED: declared topology does not match live GCP state")

    print("INFRASTRUCTURE DRIFT CHECK PASSED")


if __name__ == "__main__":
    main()
