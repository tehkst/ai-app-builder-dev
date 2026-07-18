from unittest.mock import patch

from app.platform.deployment.production_verification import run_automatic_production_verification, run_production_verification


def main() -> None:
    payload = {
        "token": "founder-session",
        "service_url": "https://production.example.test",
        "service_name": "production-service",
    }
    root = {"name": "service_url_reachable", "passed": True, "status_code": 200, "response_time_ms": 10, "detail": "HTTP 200", "body_contains_brand": True}
    optional = {"name": "optional", "passed": True, "status_code": 200, "response_time_ms": 10, "detail": "HTTP 200"}
    with patch("app.platform.deployment.production_verification.require_founder", return_value={"authorized": True}), patch("app.platform.deployment.production_verification._http_check", side_effect=[root, optional, optional, optional]), patch("app.platform.deployment.production_verification.record_operational_evidence", return_value={"evidence_id": "EVIDENCE-1", "observed_at": "2026-07-18T00:00:00+00:00"}) as persist:
        result = run_production_verification(payload)
    assert result["overall_result"] == "pass"
    assert result["evidence_id"] == "EVIDENCE-1"
    assert persist.call_args.args[0] == "production_verification"
    assert persist.call_args.args[4]["checks"]

    with patch("app.platform.deployment.production_verification.require_founder", return_value={"authorized": False}), patch("app.platform.deployment.production_verification.record_operational_evidence") as blocked_persist:
        blocked = run_production_verification(payload)
    assert blocked["overall_result"] == "fail"
    blocked_persist.assert_not_called()

    with patch.dict("os.environ", {"K_REVISION": "revision-live"}, clear=False), patch("app.platform.deployment.production_verification._http_check", side_effect=[root, optional, optional, optional]), patch("app.platform.deployment.production_verification.record_operational_evidence", return_value={"evidence_id": "EVIDENCE-2", "observed_at": "2026-07-18T00:01:00+00:00"}) as automatic_persist:
        automatic = run_automatic_production_verification()
    assert automatic["overall_result"] == "pass"
    assert automatic["revision_name"] == "revision-live"
    assert automatic["verification_mode"] == "automatic-read-only-revision-check"
    assert automatic_persist.called
    print("Production verification durable evidence checks passed")


if __name__ == "__main__":
    main()
