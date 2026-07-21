from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.platform.events.durable_store import DurableOrganizationalEventStore
from app.platform.events.event_models import AuthorityReference, build_organizational_event
from app.platform.persistence.models import PlatformBase


def run_check() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    ensure_schema = lambda: PlatformBase.metadata.create_all(bind=engine)
    store = DurableOrganizationalEventStore(
        session_factory=session_factory,
        ensure_schema=ensure_schema,
    )

    event = build_organizational_event(
        "mission.workflow.created",
        source="mission_runtime",
        source_authority="PlatformWorkflowRun",
        aggregate_type="mission",
        aggregate_id="MISSION-CHECK-001",
        idempotency_key="ORG-IDEMP-CHECK-001",
        evidence_references=("WORKFLOW-RUN-CHECK-001",),
        authority_references=(
            AuthorityReference(
                "PlatformWorkflowRun",
                "WORKFLOW-RUN-CHECK-001",
                "authoritative_source",
            ),
        ),
        payload={"workflow_run_id": "WORKFLOW-RUN-CHECK-001"},
        occurred_at=datetime.now(timezone.utc),
    )

    first = store.append(event)
    replay = store.append(event)
    timeline = store.list_for_aggregate("mission", "MISSION-CHECK-001")

    assert first["replayed"] is False
    assert first["authoritative"] is False
    assert replay["replayed"] is True
    assert replay["event_id"] == first["event_id"]
    assert len(timeline) == 1
    assert timeline[0]["source_authority"] == "PlatformWorkflowRun"
    assert timeline[0]["evidence_references"] == ["WORKFLOW-RUN-CHECK-001"]
    assert timeline[0]["authority_references"] == [
        {
            "authority": "PlatformWorkflowRun",
            "entity_id": "WORKFLOW-RUN-CHECK-001",
            "relationship": "authoritative_source",
        }
    ]
    assert "authority_references" not in timeline[0]["metadata"]
    assert store.get_by_idempotency_key("ORG-IDEMP-CHECK-001") is not None


if __name__ == "__main__":
    run_check()
    print("durable organizational event store check: PASS")
