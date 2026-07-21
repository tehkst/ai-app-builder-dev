from __future__ import annotations

from app.platform.events.company_brain_query_service import CompanyBrainQueryService
from app.platform.events.knowledge_projection import (
    GovernedKnowledgeProjection,
    KnowledgeEdge,
    KnowledgeNode,
)


class _ProjectionService:
    def build_from_aggregate(self, aggregate_type, aggregate_id):
        assert aggregate_type == "mission"
        assert aggregate_id == "MISSION-1"
        return GovernedKnowledgeProjection(
            nodes=(
                KnowledgeNode("PlatformWorkflowRun", "WF-1"),
                KnowledgeNode("PlatformAgentTask", "TASK-1"),
                KnowledgeNode("PlatformOperationalEvidence", "EVIDENCE-1"),
                KnowledgeNode("PlatformWorkspaceArtifact", "CHANGE-1"),
            ),
            edges=(
                KnowledgeEdge(
                    "PlatformWorkflowRun:WF-1",
                    "PlatformAgentTask:TASK-1",
                    "parent_workflow",
                    "EVENT-1",
                ),
                KnowledgeEdge(
                    "PlatformWorkflowRun:WF-1",
                    "PlatformOperationalEvidence:EVIDENCE-1",
                    "supporting_evidence",
                    "EVENT-2",
                ),
                KnowledgeEdge(
                    "PlatformWorkflowRun:WF-1",
                    "PlatformWorkspaceArtifact:CHANGE-1",
                    "supporting_evidence",
                    "EVENT-3",
                ),
            ),
            event_ids=("EVENT-1", "EVENT-2", "EVENT-3"),
        )


def main() -> None:
    service = CompanyBrainQueryService(_ProjectionService())

    graph = service.get_mission_graph("MISSION-1")
    assert graph.authoritative is False
    assert len(graph.entities) == 4
    assert len(graph.relationships) == 3
    assert graph.supporting_event_ids == ("EVENT-1", "EVENT-2", "EVENT-3")

    related = service.related_entities(
        "PlatformWorkflowRun",
        "WF-1",
        root_aggregate_id="MISSION-1",
    )
    assert tuple(entity.key for entity in related) == (
        "PlatformAgentTask:TASK-1",
        "PlatformOperationalEvidence:EVIDENCE-1",
        "PlatformWorkspaceArtifact:CHANGE-1",
    )

    lineage = service.get_entity_lineage(
        "PlatformAgentTask",
        "TASK-1",
        root_aggregate_id="MISSION-1",
    )
    assert len(lineage.entities) == 4
    assert lineage.supporting_event_ids == ("EVENT-1", "EVENT-2", "EVENT-3")

    evidence = service.find_supporting_evidence(
        "PlatformAgentTask",
        "TASK-1",
        root_aggregate_id="MISSION-1",
    )
    assert tuple(entity.key for entity in evidence) == (
        "PlatformOperationalEvidence:EVIDENCE-1",
        "PlatformWorkspaceArtifact:CHANGE-1",
    )

    explanation = service.explain_entity(
        "PlatformAgentTask",
        "TASK-1",
        root_aggregate_id="MISSION-1",
    )
    assert explanation.subject.key == "PlatformAgentTask:TASK-1"
    assert len(explanation.related_entities) == 3
    assert explanation.supporting_event_ids == ("EVENT-1", "EVENT-2", "EVENT-3")

    try:
        service.get_entity_lineage("", "TASK-1", root_aggregate_id="MISSION-1")
    except ValueError as exc:
        assert str(exc) == "entity_type is required"
    else:
        raise AssertionError("empty entity_type must fail")

    print("company brain query service: PASS")


if __name__ == "__main__":
    main()
