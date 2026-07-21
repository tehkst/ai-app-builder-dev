from __future__ import annotations

from app.platform.events.company_brain_impact_analyzer import CompanyBrainImpactAnalyzer
from app.platform.events.company_brain_models import (
    CompanyBrainEntity,
    CompanyBrainExplanation,
    CompanyBrainRelationship,
)
from app.platform.events.company_brain_reasoning_models import ImpactSummary


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
        assert entity_id == "workflow-1"
        assert root_aggregate_type == "mission"
        assert root_aggregate_id == "mission-1"
        return CompanyBrainExplanation(
            subject=CompanyBrainEntity("PlatformWorkflowRun", "workflow-1"),
            related_entities=(
                CompanyBrainEntity("PlatformExecutionEvidence", "evidence-1"),
                CompanyBrainEntity("PlatformMission", "mission-1"),
                CompanyBrainEntity("PlatformRelease", "release-1"),
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
                    target_key="PlatformWorkspaceArtifact:artifact-1",
                    relationship="produced",
                    supporting_event_ids=("event-2",),
                ),
                CompanyBrainRelationship(
                    source_key="PlatformWorkspaceArtifact:artifact-1",
                    target_key="PlatformRelease:release-1",
                    relationship="included_in",
                    supporting_event_ids=("event-3",),
                ),
                CompanyBrainRelationship(
                    source_key="PlatformWorkflowRun:workflow-1",
                    target_key="PlatformExecutionEvidence:evidence-1",
                    relationship="supported_by",
                    supporting_event_ids=("event-4",),
                ),
            ),
            supporting_event_ids=("event-1", "event-2", "event-3", "event-4"),
            authoritative=True,
        )


def _check_impact() -> None:
    summary = CompanyBrainImpactAnalyzer(_FakeCompanyBrainQueryService()).analyze(
        "PlatformWorkflowRun",
        "workflow-1",
        root_aggregate_id="mission-1",
    )

    assert isinstance(summary, ImpactSummary)
    assert summary.subject.key == "PlatformWorkflowRun:workflow-1"
    assert tuple(entity.key for entity in summary.upstream) == (
        "PlatformMission:mission-1",
    )
    assert tuple(entity.key for entity in summary.downstream) == (
        "PlatformExecutionEvidence:evidence-1",
        "PlatformWorkspaceArtifact:artifact-1",
    )
    assert tuple(entity.key for entity in summary.affected) == (
        "PlatformExecutionEvidence:evidence-1",
        "PlatformRelease:release-1",
        "PlatformWorkspaceArtifact:artifact-1",
    )
    assert summary.risk_score == 65
    assert summary.supporting_event_ids == (
        "event-1",
        "event-2",
        "event-3",
        "event-4",
    )
    assert summary.authoritative is True
    assert summary.as_dict()["risk_score"] == 65


def _check_isolated_subject() -> None:
    class EmptyBrain:
        def explain_entity(
            self,
            entity_type: str,
            entity_id: str,
            *,
            root_aggregate_type: str = "mission",
            root_aggregate_id: str | None = None,
        ) -> CompanyBrainExplanation:
            return CompanyBrainExplanation(
                subject=CompanyBrainEntity(entity_type, entity_id),
            )

    summary = CompanyBrainImpactAnalyzer(EmptyBrain()).analyze(
        "PlatformWorkflowRun",
        "isolated",
    )
    assert summary.upstream == ()
    assert summary.downstream == ()
    assert summary.affected == ()
    assert summary.risk_score == 0
    assert summary.supporting_event_ids == ()


def _check_validation() -> None:
    analyzer = CompanyBrainImpactAnalyzer(_FakeCompanyBrainQueryService())
    try:
        analyzer.analyze(" ", "workflow-1")
    except ValueError as error:
        assert str(error) == "entity_type is required"
    else:
        raise AssertionError("blank entity_type must fail")

    try:
        analyzer.analyze("PlatformWorkflowRun", " ")
    except ValueError as error:
        assert str(error) == "entity_id is required"
    else:
        raise AssertionError("blank entity_id must fail")


def main() -> None:
    _check_impact()
    _check_isolated_subject()
    _check_validation()
    print("impact analyzer: PASS")


if __name__ == "__main__":
    main()
