from __future__ import annotations

from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.platform.persistence.models import PlatformAgentTask, PlatformBase
from app.platform.services.agent_task_service import claim_next_agent_task, finalize_claimed_agent_task, recover_expired_agent_tasks, renew_agent_task_lease, utc_now


def main() -> None:
    engine = create_engine("sqlite:///:memory:")
    PlatformBase.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add(PlatformAgentTask(task_id="TASK-LEASE-SAFETY", title="Lease safety", status="queued", priority="high", risk_level="low", task_type="lease_safety", requested_by="check", input_payload_json="{}", result_payload_json="{}", approval_required=False, max_attempts=3))
    db.commit()

    worker_a = claim_next_agent_task(db, assigned_agent="worker-a", task_type="lease_safety")
    assert worker_a and worker_a["assigned_agent"] == "worker-a"
    assert renew_agent_task_lease(db, task_id=worker_a["task_id"], lease_owner="worker-a") is True
    assert renew_agent_task_lease(db, task_id=worker_a["task_id"], lease_owner="worker-b") is False
    assert recover_expired_agent_tasks(db, lease_seconds=120) == 0

    row = db.query(PlatformAgentTask).filter_by(task_id=worker_a["task_id"]).first()
    row.claimed_at = utc_now() - timedelta(seconds=121)
    db.commit()
    assert recover_expired_agent_tasks(db, lease_seconds=120) == 1
    worker_b = claim_next_agent_task(db, assigned_agent="worker-b", task_type="lease_safety")
    assert worker_b and worker_b["assigned_agent"] == "worker-b"

    stale = finalize_claimed_agent_task(db, task_id=worker_a["task_id"], lease_owner="worker-a", status="completed", result_payload={"owner": "worker-a"})
    assert stale is None
    completed = finalize_claimed_agent_task(db, task_id=worker_b["task_id"], lease_owner="worker-b", status="completed", result_payload={"owner": "worker-b"})
    assert completed and completed["result_payload"] == {"owner": "worker-b"}
    print("agent task lease renewal and owner fencing ok")


if __name__ == "__main__":
    main()
