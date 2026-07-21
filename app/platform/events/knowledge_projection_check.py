from __future__ import annotations

from app.platform.events.knowledge_projection import build_governed_knowledge_projection


def main() -> None:
    events = [
        {
            "event_id": "ORG-EVT-1",
            "authority_references": [
                {
                    "authority": "PlatformWorkflowRun",
                    "entity_id": "RUN-1",
                    "relationship": "authoritative_source",
                },
                {
                    "authority": "PlatformOperationalEvidence",
                    "entity_id": "EVIDENCE-1",
                    "relationship": "supporting_evidence",
                },
            ],
        },
        {
            "event_id": "ORG-EVT-2",
            "authority_references": [
                {
                    "authority": "PlatformAgentTask",
                    "entity_id": "TASK-1",
                    "relationship": "authoritative_source",
                },
                {
                    "authority": "PlatformWorkflowRun",
                    "entity_id": "RUN-1",
                    "relationship": "parent_workflow",
                },
            ],
        },
        {"event_id": "ORG-EVT-LEGACY", "authority_references": []},
    ]

    projection = build_governed_knowledge_projection(events)
    serialized = projection.as_dict()

    assert projection.authoritative is False
    assert serialized["event_ids"] == ["ORG-EVT-1", "ORG-EVT-2", "ORG-EVT-LEGACY"]
    assert serialized["nodes"] == [
        {"authority": "PlatformAgentTask", "entity_id": "TASK-1"},
        {"authority": "PlatformOperationalEvidence", "entity_id": "EVIDENCE-1"},
        {"authority": "PlatformWorkflowRun", "entity_id": "RUN-1"},
    ]
    assert serialized["edges"] == [
        {
            "source_key": "PlatformAgentTask:TASK-1",
            "target_key": "PlatformWorkflowRun:RUN-1",
            "relationship": "parent_workflow",
            "event_id": "ORG-EVT-2",
        },
        {
            "source_key": "PlatformWorkflowRun:RUN-1",
            "target_key": "PlatformOperationalEvidence:EVIDENCE-1",
            "relationship": "supporting_evidence",
            "event_id": "ORG-EVT-1",
        },
    ]

    replayed = build_governed_knowledge_projection(reversed(events))
    assert replayed.as_dict()["nodes"] == serialized["nodes"]
    assert replayed.as_dict()["edges"] == serialized["edges"]

    print("governed knowledge projection: PASS")


if __name__ == "__main__":
    main()
