from __future__ import annotations

from app.platform.events.company_brain_models import (
    CompanyBrainEntity,
    CompanyBrainGraph,
    CompanyBrainRelationship,
)
from app.platform.events.company_brain_twin_engine import CompanyBrainTwinEngine
from app.platform.events.company_brain_twin_models import (
    TWIN_ALIGNED,
    TWIN_MISSING,
    TWIN_UNEXPECTED,
)


MISSION = CompanyBrainEntity("PlatformMission", "mission-1")
REPOSITORY = CompanyBrainEntity("PlatformRepository", "repo-1")
SERVICE = CompanyBrainEntity("PlatformService", "service-1")
UNEXPECTED = CompanyBrainEntity("PlatformService", "service-shadow")

MISSION_REPOSITORY = CompanyBrainRelationship(
    MISSION.key,
    REPOSITORY.key,
    "contains",
    ("event-1",),
)
REPOSITORY_SERVICE = CompanyBrainRelationship(
    REPOSITORY.key,
    SERVICE.key,
    "contains",
    ("event-2",),
)


class _FakeQueryService:
    def __init__(self, graph: CompanyBrainGraph) -> None:
        self.graph = graph
        self.calls = []

    def get_mission_graph(self, mission_id: str) -> CompanyBrainGraph:
        self.calls.append(mission_id)
        assert mission_id == "mission-1"
        return self.graph


def _desired_graph() -> CompanyBrainGraph:
    return CompanyBrainGraph(
        entities=(SERVICE, MISSION, REPOSITORY),
        relationships=(REPOSITORY_SERVICE, MISSION_REPOSITORY),
        supporting_event_ids=("event-1", "event-2"),
        authoritative=True,
    )


def _engine():
    query = _FakeQueryService(_desired_graph())
    return CompanyBrainTwinEngine(query), query


def _check_snapshot() -> None:
    engine, query = _engine()
    snapshot = engine.build_snapshot("mission-1")
    assert query.calls == ["mission-1"]
    assert snapshot.mission == MISSION
    assert snapshot.observed_graph is None
    assert snapshot.reconciled is False
    assert snapshot.aligned is False
    assert snapshot.authoritative is True
    assert [item.entity.key for item in snapshot.components] == sorted(
        (MISSION.key, REPOSITORY.key, SERVICE.key)
    )
    assert all(item.status == TWIN_ALIGNED for item in snapshot.components)
    assert [item.relationship for item in snapshot.topology] == ["contains", "contains"]
    payload = snapshot.as_dict()
    assert payload["reconciled"] is False
    assert payload["observed_graph"] is None


def _check_aligned_reconciliation() -> None:
    engine, _ = _engine()
    observed = CompanyBrainGraph(
        entities=(MISSION, REPOSITORY, SERVICE),
        relationships=(MISSION_REPOSITORY, REPOSITORY_SERVICE),
        supporting_event_ids=("observed-1",),
        authoritative=True,
    )
    snapshot = engine.reconcile("mission-1", observed)
    assert snapshot.reconciled is True
    assert snapshot.aligned is True
    assert snapshot.drift == ()
    assert snapshot.authoritative is True
    assert snapshot.supporting_event_ids == ("event-1", "event-2", "observed-1")


def _check_component_drift() -> None:
    engine, _ = _engine()
    observed = CompanyBrainGraph(
        entities=(MISSION, REPOSITORY, UNEXPECTED),
        relationships=(MISSION_REPOSITORY,),
        supporting_event_ids=("observed-2",),
        authoritative=True,
    )
    snapshot = engine.reconcile("mission-1", observed)
    status_by_key = {item.entity.key: item.status for item in snapshot.components}
    assert status_by_key[SERVICE.key] == TWIN_MISSING
    assert status_by_key[UNEXPECTED.key] == TWIN_UNEXPECTED
    assert {item.code for item in snapshot.drift} == {
        "TWIN_COMPONENTS_MISSING",
        "TWIN_COMPONENTS_UNEXPECTED",
        "TWIN_RELATIONSHIPS_MISSING",
    }
    assert snapshot.aligned is False
    assert snapshot.authoritative is False


def _check_relationship_drift() -> None:
    engine, _ = _engine()
    unexpected_relationship = CompanyBrainRelationship(
        MISSION.key,
        SERVICE.key,
        "deploys",
        ("observed-3",),
    )
    observed = CompanyBrainGraph(
        entities=(MISSION, REPOSITORY, SERVICE),
        relationships=(MISSION_REPOSITORY, unexpected_relationship),
        supporting_event_ids=("observed-3",),
        authoritative=True,
    )
    snapshot = engine.reconcile("mission-1", observed)
    assert {item.code for item in snapshot.drift} == {
        "TWIN_RELATIONSHIPS_MISSING",
        "TWIN_RELATIONSHIPS_UNEXPECTED",
    }
    assert snapshot.authoritative is True
    assert snapshot.aligned is False


def _check_non_authoritative_observation() -> None:
    engine, _ = _engine()
    observed = CompanyBrainGraph(
        entities=(MISSION, REPOSITORY, SERVICE),
        relationships=(MISSION_REPOSITORY, REPOSITORY_SERVICE),
        supporting_event_ids=("observed-4",),
        authoritative=False,
    )
    snapshot = engine.reconcile("mission-1", observed)
    assert snapshot.authoritative is False
    assert "Observed topology is not authoritative." in snapshot.warnings


def _check_missing_governed_topology() -> None:
    query = _FakeQueryService(CompanyBrainGraph())
    engine = CompanyBrainTwinEngine(query)
    snapshot = engine.build_snapshot("mission-1")
    assert snapshot.authoritative is False
    assert snapshot.mission.key == "PlatformMission:mission-1"
    assert snapshot.warnings == ("No governed mission topology is available.",)


def _check_validation() -> None:
    engine, _ = _engine()
    try:
        engine.build_snapshot(" ")
    except ValueError as error:
        assert str(error) == "mission_id is required"
    else:
        raise AssertionError("blank mission id must fail")

    try:
        engine.reconcile("mission-1", object())
    except TypeError as error:
        assert str(error) == "observed_graph must be a CompanyBrainGraph"
    else:
        raise AssertionError("invalid observed graph must fail")


def main() -> None:
    _check_snapshot()
    _check_aligned_reconciliation()
    _check_component_drift()
    _check_relationship_drift()
    _check_non_authoritative_observation()
    _check_missing_governed_topology()
    _check_validation()
    print("company brain digital twin engine: PASS")


if __name__ == "__main__":
    main()
