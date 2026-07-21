from __future__ import annotations

from app.platform.events.company_brain_models import (
    CompanyBrainEntity,
    CompanyBrainExplanation,
    CompanyBrainRelationship,
)
from app.platform.events.company_brain_reasoning_models import RootCauseSummary
from app.platform.events.company_brain_root_cause_analyzer import (
    CompanyBrainRootCauseAnalyzer,
)


class _FakeCompanyBrainQueryService:
    def explain_entity(
        self,
        entity_type: str,
        entity_id: str,
        *,
        root_aggregate_type: str = "mission",
        root_aggregate_id: str | None = None,
    ) -> CompanyBrainExplanation:
        assert entity_type == "PlatformWorkflowRun"
        assert entity_id == "workflow-failed"
        assert root_aggregate_type == "mission"
        assert root_aggregate_id == "mission-1"
        return CompanyBrainExplanation(
            subject=CompanyBrainEntity("PlatformWorkflowRun", "workflow-failed"),
            related_entities=(
                CompanyBrainEntity("PlatformExecutionEvidence", "evidence-1"),
                CompanyBrainEntity("PlatformTaskRun", "task-1"),
                CompanyBrainEntity("PlatformWorkspaceArtifact", "artifact-1"),
            ),
            relationships=(
                CompanyBrainRelationship(
                    source_key="PlatformTaskRun:task-1",
                    target_key="PlatformWorkflowRun:workflow-failed",
                    relationship="blocked",
                    supporting_event_ids=("event-2",),
                ),
                CompanyBrainRelationship(
                    source_key="PlatformExecutionEvidence:evidence-1",
                    target_key="PlatformTaskRun:task-1",
                    relationship="supports",
                    supporting_event_ids=("event-3",),
                ),
                CompanyBrainRelationship(
                    source_key="PlatformWorkspaceArtifact:artifact-1",
                    target_key="PlatformWorkflowRun:workflow-failed",
                    relationship="invalidated",
                    supporting_event_ids=("event-1",),
                ),
            ),
            supporting_event_ids=("event-1", "event-2", "event-3"),
            authoritative=True,
        )


def _check_analysis() -> None:
    analyzer = CompanyBrainRootCauseAnalyzer(_FakeCompanyBrainQueryService())
    summary = analyzer.analyze(
        "PlatformWorkflowRun",
        "workflow-failed",
        root_aggregate_id="mission-1",
    )

    assert isinstance(summary, RootCauseSummary)
    assert summary.failure.key == "PlatformWorkflowRun:workflow-failed"
    assert tuple(finding.description for finding in summary.contributing_factors) == (
        "PlatformTaskRun:task-1 blocked PlatformWorkflowRun:workflow-failed",
        "PlatformWorkspaceArtifact:artifact-1 invalidated PlatformWorkflowRun:workflow-failed",
    )
    assert tuple(item.entity.key for item in summary.evidence) == (
        "PlatformExecutionEvidence:evidence-1",
        "PlatformWorkspaceArtifact:artifact-1",
    )
    assert summary.evidence[0].supporting_event_ids == ("event-3",)
    assert summary.evidence[1].supporting_event_ids == ("event-1",)
    assert summary.likely_cause == "PlatformTaskRun:task-1 via blocked"
    assert summary.confidence == 0.9
    assert summary.supporting_event_ids == ("event-1", "event-2", "event-3")
    assert summary.authoritative is True
    assert summary.as_dict()["failure"]["entity_id"] == "workflow-failed"


def _check_no_contributing_relationship() -> None:
    class EmptyBrain:
        def explain_entity(self, *args, **kwargs) -> CompanyBrainExplanation:
            return CompanyBrainExplanation(
                subject=CompanyBrainEntity("PlatformWorkflowRun", "isolated"),
            )

    summary = CompanyBrainRootCauseAnalyzer(EmptyBrain()).analyze(
        "PlatformWorkflowRun",
        "isolated",
    )
    assert summary.contributing_factors == ()
    assert summary.likely_cause == "No governed contributing relationship was found."
    assert summary.confidence == 0.0


def _check_validation() -> None:
    analyzer = CompanyBrainRootCauseAnalyzer(_FakeCompanyBrainQueryService())
    for entity_type, entity_id, expected in (
        (" ", "workflow-failed", "entity_type is required"),
        ("PlatformWorkflowRun", " ", "entity_id is required"),
    ):
        try:
            analyzer.analyze(entity_type, entity_id)
        except ValueError as error:
            assert str(error) == expected
        else:
            raise AssertionError("blank identifiers must fail")


def main() -> None:
    _check_analysis()
    _check_no_contributing_relationship()
    _check_validation()
    print("root cause analyzer: PASS")


if __name__ == "__main__":
    main()
