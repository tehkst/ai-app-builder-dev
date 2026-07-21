from __future__ import annotations

from app.platform.events.company_brain_execution_summary_service import (
    CompanyBrainExecutionSummaryService,
)
from app.platform.events.company_brain_models import (
    CompanyBrainEntity,
    CompanyBrainGraph,
    CompanyBrainRelationship,
)
from app.platform.events.company_brain_reasoning_models import ExecutionSummary


class _FakeCompanyBrainQueryService:
    def get_mission_graph(self, mission_id: str) -> CompanyBrainGraph:
        assert mission_id == "mission-1"
        return CompanyBrainGraph(
            entities=(
                CompanyBrainEntity("PlatformExecutionEvidence", "evidence-1"),
                CompanyBrainEntity("PlatformMission", "mission-1"),
                CompanyBrainEntity("PlatformWorkflowRun", "workflow-1"),
                CompanyBrainEntity("PlatformWorkspaceArtifact", "artifact-1"),
            ),
            relationships=(
                CompanyBrainRelationship(
                    source_key="PlatformMission:mission-1",
                    target_key="PlatformWorkflowRun:workflow-1",
                    relationship="initiated",
                    supporting_event_ids=("event-1",),
                ),
                CompanyBrainRelationship(
                    source_key="PlatformWorkflowRun:workflow-1",
                    target_key="PlatformExecutionEvidence:evidence-1",
                    relationship="supported_by",
                    supporting_event_ids=("event-2",),
                ),
                CompanyBrainRelationship(
                    source_key="PlatformWorkflowRun:workflow-1",
                    target_key="PlatformWorkspaceArtifact:artifact-1",
                    relationship="produced",
                    supporting_event_ids=("event-3",),
                ),
            ),
            supporting_event_ids=("event-1", "event-2", "event-3"),
        )


def _check_summary() -> None:
    service = CompanyBrainExecutionSummaryService(_FakeCompanyBrainQueryService())
    summary = service.summarize_mission("mission-1")

    assert isinstance(summary, ExecutionSummary)
    assert summary.mission.key == "PlatformMission:mission-1"
    assert tuple(entity.key for entity in summary.entities) == (
        "PlatformExecutionEvidence:evidence-1",
        "PlatformMission:mission-1",
        "PlatformWorkflowRun:workflow-1",
        "PlatformWorkspaceArtifact:artifact-1",
    )
    assert tuple(item.entity.key for item in summary.evidence) == (
        "PlatformExecutionEvidence:evidence-1",
        "PlatformWorkspaceArtifact:artifact-1",
    )
    assert summary.evidence[0].supporting_event_ids == ("event-2",)
    assert summary.evidence[1].supporting_event_ids == ("event-3",)
    assert tuple(finding.code for finding in summary.findings) == (
        "MISSION_GRAPH_SUMMARY",
        "SUPPORTING_EVIDENCE_PRESENT",
    )
    assert summary.warnings == ()
    assert summary.supporting_event_ids == ("event-1", "event-2", "event-3")
    assert summary.authoritative is False
    assert summary.as_dict()["mission"]["entity_id"] == "mission-1"


def _check_empty_graph() -> None:
    class EmptyBrain:
        def get_mission_graph(self, mission_id: str) -> CompanyBrainGraph:
            return CompanyBrainGraph()

    summary = CompanyBrainExecutionSummaryService(EmptyBrain()).summarize_mission("missing")
    assert summary.mission.key == "PlatformMission:missing"
    assert summary.entities == ()
    assert summary.warnings == ("No governed entities were found for the mission.",)
    assert summary.findings[-1].severity == "warning"


def _check_validation() -> None:
    try:
        CompanyBrainExecutionSummaryService(_FakeCompanyBrainQueryService()).summarize_mission(" ")
    except ValueError as error:
        assert str(error) == "mission_id is required"
    else:
        raise AssertionError("blank mission_id must fail")


def main() -> None:
    _check_summary()
    _check_empty_graph()
    _check_validation()
    print("execution summary service: PASS")


if __name__ == "__main__":
    main()
