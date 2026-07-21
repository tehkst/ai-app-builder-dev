from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.platform.events.aggregate_knowledge_projection import (
    AggregateKnowledgeProjectionService,
    build_projection_for_aggregate,
)
from app.platform.events.durable_store import DurableOrganizationalEventStore
from app.platform.events.event_models import AuthorityReference, build_organizational_event
from app.platform.persistence.models import PlatformBase


def main() -> None:
    engine = create_engine("sqlite:///:memory:")
    session_factory = sessionmaker(bind=engine)
    ensure_schema = lambda: PlatformBase.metadata.create_all(bind=engine)
    store = DurableOrganizationalEventStore(
        session_factory=session_factory,
        ensure_schema=ensure_schema,
    )

    event = build_organizational_event(
        event_type="mission.change_set_verified",
        source="mission_lifecycle",
        source_authority="PlatformWorkflowRun",
        aggregate_type="mission",
        aggregate_id="MISSION-KNOW-03",
        idempotency_key="ORG-KNOW-03-K2-CHECK",
        authority_references=(
            AuthorityReference(
                "PlatformWorkflowRun",
                "WORKFLOW-KNOW-03",
                "authoritative_source",
            ),
            AuthorityReference(
                "PlatformExecutionEvidence",
                "VALIDATION-KNOW-03",
                "supporting_evidence",
            ),
        ),
        occurred_at=datetime.now(timezone.utc),
    )
    store.append(event)

    service = AggregateKnowledgeProjectionService(store)
    projection = service.build_for_aggregate(" mission ", " MISSION-KNOW-03 ")

    assert projection.authoritative is False
    assert projection.event_ids == (event.event_id,)
    assert [node.key for node in projection.nodes] == [
        "PlatformExecutionEvidence:VALIDATION-KNOW-03",
        "PlatformWorkflowRun:WORKFLOW-KNOW-03",
    ]
    assert [edge.as_dict() for edge in projection.edges] == [
        {
            "source_key": "PlatformWorkflowRun:WORKFLOW-KNOW-03",
            "target_key": "PlatformExecutionEvidence:VALIDATION-KNOW-03",
            "relationship": "supporting_evidence",
            "event_id": event.event_id,
        }
    ]

    convenience_projection = build_projection_for_aggregate(
        "mission",
        "MISSION-KNOW-03",
        store=store,
    )
    assert convenience_projection.as_dict() == projection.as_dict()

    empty = service.build_for_aggregate("mission", "MISSION-NOT-FOUND")
    assert empty.as_dict() == {
        "nodes": [],
        "edges": [],
        "event_ids": [],
        "authoritative": False,
    }

    try:
        service.build_for_aggregate("", "MISSION-KNOW-03")
    except ValueError as exc:
        assert str(exc) == "aggregate_type is required"
    else:
        raise AssertionError("missing aggregate_type should fail")

    try:
        service.build_for_aggregate("mission", "")
    except ValueError as exc:
        assert str(exc) == "aggregate_id is required"
    else:
        raise AssertionError("missing aggregate_id should fail")

    print("aggregate governed knowledge projection: PASS")


if __name__ == "__main__":
    main()
