from __future__ import annotations

import uuid
from unittest.mock import patch

from app.platform.persistence.database import PlatformSessionLocal
from app.platform.persistence.models import PlatformValidationMission, PlatformValidationStep
from app.platform.validation.catalogue import VALIDATION_CATALOGUE, validation_catalogue
from app.platform.validation.engine import execute_validation_mission, validation_mission_status
from app.platform.validation.service import build_acceptance_report, latest_capability_validation


def main() -> None:
    suffix = uuid.uuid4().hex[:10].upper()
    created = []
    assert execute_validation_mission({"validation_type": "repository", "execution_mode": "test"})["status"] == "denied"

    def successful_executor(capability, payload):
        assert payload["token"] is None
        return {"status": "completed", "governance_evidence": {"evidence_id": "TEST-%s" % capability}}

    for validation_type in VALIDATION_CATALOGUE:
        validation_id = "VALIDATION-TEST-%s-%s" % (validation_type.upper(), suffix)
        created.append(validation_id)
        result = execute_validation_mission({
            "validation_mission_id": validation_id,
            "validation_type": validation_type,
            "execution_mode": "test",
        }, executor=successful_executor, allow_test_mode=True)
        assert result["final_result"] == "pass", validation_type
        assert len(result["steps"]) == len(VALIDATION_CATALOGUE[validation_type])
        assert all(step["verification"]["acceptance_eligible"] is False for step in result["steps"])
        assert validation_mission_status(validation_id)["status"] == "completed"

    live_id = "VALIDATION-LIVE-REPOSITORY-%s" % suffix
    created.append(live_id)
    with patch("app.platform.validation.engine.require_founder", return_value={"authorized": True}):
        live = execute_validation_mission({
            "validation_mission_id": live_id, "validation_type": "repository",
            "execution_mode": "live", "token": "never-persist-this-token",
        }, executor=lambda capability, payload: {
            "status": "completed", "governance_evidence": {"evidence_id": "LIVE-%s" % capability},
        })
    assert live["final_result"] == "pass"
    assert latest_capability_validation("repository_checkout")["status"] == "pass"
    partial_acceptance = build_acceptance_report()
    assert partial_acceptance["status"] == "unknown" and partial_acceptance["accepted"] is False
    repository_acceptance = next(row for row in partial_acceptance["missions"] if row["validation_type"] == "repository")
    assert repository_acceptance["status"] == "pass"
    blocked_id = "VALIDATION-BLOCKED-GITHUB-%s" % suffix
    created.append(blocked_id)
    blocked = execute_validation_mission({
        "validation_mission_id": blocked_id, "validation_type": "github", "execution_mode": "test",
    }, executor=lambda capability, payload: {
        "status": "blocked_by_trust_prerequisite", "reason": "Independent reviewer required.",
    } if capability == "github_approve_pr" else {"status": "completed"}, allow_test_mode=True)
    assert blocked["final_result"] == "blocked_by_trust_prerequisite"
    assert any(step["status"] == "blocked_by_trust_prerequisite" for step in blocked["steps"])
    with PlatformSessionLocal() as db:
        persisted = db.query(PlatformValidationStep).filter_by(validation_mission_id=live_id).first()
        assert "never-persist-this-token" not in persisted.request_json
        assert "[REDACTED]" in persisted.request_json
        db.query(PlatformValidationStep).filter(PlatformValidationStep.validation_mission_id.in_(created)).delete(synchronize_session=False)
        db.query(PlatformValidationMission).filter(PlatformValidationMission.validation_mission_id.in_(created)).delete(synchronize_session=False)
        db.commit()

    assert len(validation_catalogue()) == 8
    print("Platform validation framework checks passed")


if __name__ == "__main__":
    main()
