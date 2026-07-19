from pathlib import Path
from unittest.mock import patch

from app.platform.governance_authorization.service import CAPABILITIES, authorize_governed_action, build_governance_authorization_summary


def main() -> None:
    recorded = {"evidence_id": "EVIDENCE-1", "observed_at": "now"}
    with patch("app.platform.governance_authorization.service.record_operational_evidence", return_value=recorded):
        with patch("app.platform.governance_authorization.service.require_founder", return_value={"authorized": False}):
            blocked = authorize_governed_action({"actor": "mission_control", "mission_id": "MISSION-1"}, "merge_pr", required_approval_phrase="APPROVE")
        assert blocked["denied"] is True and "founder approval" in blocked["reason"]
        with patch("app.platform.governance_authorization.service.require_founder", return_value={"authorized": True}):
            allowed = authorize_governed_action({"actor": "codex", "mission_id": "MISSION-1", "live_execution": True, "approval_phrase": "APPROVE"}, "merge_pr", required_approval_phrase="APPROVE")
            denied = authorize_governed_action({"actor": "codex", "mission_id": "MISSION-1", "live_execution": True, "approval_phrase": "APPROVE"}, "merge_pr", required_approval_phrase="APPROVE", policy_context={"security_policy": False})
    assert allowed["allowed"] is True and allowed["evidence_id"] == "EVIDENCE-1"
    assert denied["denied"] is True and "security policy" in denied["reason"]
    summary = build_governance_authorization_summary()
    assert len(summary["capability_matrix"]) == 35
    assert all(item["mission_control"] == item["codex"] for item in summary["capability_matrix"])
    for path in (
        "app/platform/github_execution/approved_executor.py",
        "app/platform/github_execution/approved_merge.py",
        "app/platform/deployment/approved_cloud_run.py",
        "app/platform/deployment/approved_rollback.py",
    ):
        source = Path(path).read_text(encoding="utf-8")
        assert "authorize_governed_action" in source
        assert "record_governed_outcome" in source
    print("Governance capability parity checks passed")


if __name__ == "__main__":
    main()
