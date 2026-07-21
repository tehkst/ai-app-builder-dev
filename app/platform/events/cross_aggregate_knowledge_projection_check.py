from __future__ import annotations

from typing import Any, Dict, List

from app.platform.events.cross_aggregate_knowledge_projection import (
    CrossAggregateKnowledgeProjectionService,
)


class FakeStore:
    def __init__(self) -> None:
        self.aggregate_calls: List[Dict[str, Any]] = []
        self.correlation_calls: List[Dict[str, Any]] = []

    def list_for_aggregate(self, aggregate_type: str, aggregate_id: str, limit: int = 100):
        self.aggregate_calls.append(
            {"aggregate_type": aggregate_type, "aggregate_id": aggregate_id, "limit": limit}
        )
        if aggregate_type != "mission" or aggregate_id != "MISSION-123":
            return []
        return [
            {
                "event_id": "EVT-MISSION",
                "correlation_id": "RUN-123",
                "authority_references": [
                    {
                        "authority": "PlatformWorkflowRun",
                        "entity_id": "RUN-123",
                        "relationship": "authoritative_source",
                    },
                    {
                        "authority": "PlatformOperationalEvidence",
                        "entity_id": "EVIDENCE-123",
                        "relationship": "supporting_evidence",
                    },
                ],
            }
        ]

    def list_for_correlation_id(self, correlation_id: str, limit: int = 500):
        self.correlation_calls.append({"correlation_id": correlation_id, "limit": limit})
        return [
            {
                "event_id": "EVT-MISSION",
                "correlation_id": "RUN-123",
                "authority_references": [
                    {
                        "authority": "PlatformWorkflowRun",
                        "entity_id": "RUN-123",
                        "relationship": "authoritative_source",
                    },
                    {
                        "authority": "PlatformOperationalEvidence",
                        "entity_id": "EVIDENCE-123",
                        "relationship": "supporting_evidence",
                    },
                ],
            },
            {
                "event_id": "EVT-TASK",
                "correlation_id": "RUN-123",
                "authority_references": [
                    {
                        "authority": "PlatformAgentTask",
                        "entity_id": "TASK-123",
                        "relationship": "authoritative_source",
                    },
                    {
                        "authority": "PlatformWorkflowRun",
                        "entity_id": "RUN-123",
                        "relationship": "parent_workflow",
                    },
                ],
            },
            {
                "event_id": "EVT-ARTIFACT",
                "correlation_id": "RUN-123",
                "authority_references": [
                    {
                        "authority": "PlatformWorkflowRun",
                        "entity_id": "RUN-123",
                        "relationship": "authoritative_source",
                    },
                    {
                        "authority": "PlatformWorkspaceArtifact",
                        "entity_id": "CHANGESET-123",
                        "relationship": "supporting_evidence",
                    },
                ],
            },
        ]


def main() -> None:
    store = FakeStore()
    projection = CrossAggregateKnowledgeProjectionService(store).build_from_aggregate(
        "mission",
        "MISSION-123",
        aggregate_limit=25,
        correlation_limit=250,
    )

    assert store.aggregate_calls == [
        {"aggregate_type": "mission", "aggregate_id": "MISSION-123", "limit": 25}
    ]
    assert store.correlation_calls == [{"correlation_id": "RUN-123", "limit": 250}]
    assert projection.authoritative is False
    assert projection.event_ids == ("EVT-ARTIFACT", "EVT-MISSION", "EVT-TASK")
    assert [node.key for node in projection.nodes] == [
        "PlatformAgentTask:TASK-123",
        "PlatformOperationalEvidence:EVIDENCE-123",
        "PlatformWorkflowRun:RUN-123",
        "PlatformWorkspaceArtifact:CHANGESET-123",
    ]
    assert [edge.as_dict() for edge in projection.edges] == [
        {
            "source_key": "PlatformAgentTask:TASK-123",
            "target_key": "PlatformWorkflowRun:RUN-123",
            "relationship": "parent_workflow",
            "event_id": "EVT-TASK",
        },
        {
            "source_key": "PlatformWorkflowRun:RUN-123",
            "target_key": "PlatformOperationalEvidence:EVIDENCE-123",
            "relationship": "supporting_evidence",
            "event_id": "EVT-MISSION",
        },
        {
            "source_key": "PlatformWorkflowRun:RUN-123",
            "target_key": "PlatformWorkspaceArtifact:CHANGESET-123",
            "relationship": "supporting_evidence",
            "event_id": "EVT-ARTIFACT",
        },
    ]

    empty = CrossAggregateKnowledgeProjectionService(store).build_from_aggregate(
        "mission",
        "UNKNOWN",
    )
    assert empty.nodes == ()
    assert empty.edges == ()
    assert empty.event_ids == ()

    try:
        CrossAggregateKnowledgeProjectionService(store).build_from_aggregate("", "MISSION-123")
    except ValueError as exc:
        assert str(exc) == "aggregate_type is required"
    else:
        raise AssertionError("missing aggregate_type should fail")

    print("cross aggregate governed knowledge projection: PASS")


if __name__ == "__main__":
    main()
