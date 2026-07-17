from __future__ import annotations

import os
from dataclasses import FrozenInstanceError
from threading import Thread

from app.platform.company_brain import event_publisher
from app.platform.company_brain.company_brain import CompanyBrain
from app.platform.company_brain.event_bus import InProcessEventBus
from app.platform.company_brain.event_models import create_domain_event
from app.platform.company_brain.event_store import ImmutableEventStore
from app.platform.digital_twin.twin_runtime import DigitalTwin
from app.platform.executive_ai.executive_council import ExecutiveCouncil
from app.platform.events.event_sink import emit_domain_event, reset_event_sink, set_event_sink
from app.platform.simulation.simulation_engine import SimulationEngine


def _assert_immutable() -> None:
    event = create_domain_event(
        "MissionCreated", source="check", aggregate_type="mission", aggregate_id="MISSION-1",
        payload={"nested": {"stages": ["planning"]}},
    )
    try:
        event.event_type = "MissionCompleted"  # type: ignore[misc]
        raise AssertionError("event fields must be immutable")
    except FrozenInstanceError:
        pass
    try:
        event.payload["nested"]["stages"] += ("execution",)  # type: ignore[index,operator]
        raise AssertionError("nested payload values must be immutable")
    except TypeError:
        pass


def _assert_append_only_and_replay() -> tuple[CompanyBrain, list[object]]:
    store = ImmutableEventStore()
    brain = CompanyBrain(store)
    created = create_domain_event(
        "MissionCreated", source="check", aggregate_type="mission", aggregate_id="MISSION-1",
        payload={"title": "Build company memory", "status": "created"},
    )
    advanced = create_domain_event(
        "MissionAdvanced", source="check", aggregate_type="mission", aggregate_id="MISSION-1",
        correlation_id="MISSION-1", causation_id=created.event_id,
        payload={"stage": "engineering", "status": "active"},
    )
    brain.receive(created)
    brain.receive(advanced)
    try:
        store.append(created)
        raise AssertionError("duplicate event IDs must be rejected")
    except ValueError:
        pass
    assert len(brain.timeline()) == 2
    assert len(brain.mission_history("MISSION-1")) == 2
    assert brain.replay()["event_count"] == 2
    return brain, [created, advanced]


def _assert_optional_publishing() -> None:
    original_store = event_publisher.EVENT_STORE
    original_bus = event_publisher.EVENT_BUS
    original_brain = event_publisher.COMPANY_BRAIN
    original_setting = os.environ.get(event_publisher.EVENTS_ENABLED_ENV)
    try:
        event_publisher.EVENT_STORE = ImmutableEventStore()
        event_publisher.EVENT_BUS = InProcessEventBus()
        event_publisher.COMPANY_BRAIN = CompanyBrain(event_publisher.EVENT_STORE)
        event_publisher.EVENT_BUS.subscribe("*", event_publisher.COMPANY_BRAIN.project)
        received = []
        event_publisher.EVENT_BUS.subscribe("*", received.append)
        event_publisher.EVENT_BUS.subscribe("*", lambda _event: (_ for _ in ()).throw(RuntimeError("isolated")))

        os.environ[event_publisher.EVENTS_ENABLED_ENV] = "false"
        assert event_publisher.publish_domain_event(
            "MissionCreated", source="check", aggregate_type="mission", aggregate_id="MISSION-OFF",
        ) is None
        assert event_publisher.EVENT_STORE.all() == []

        os.environ[event_publisher.EVENTS_ENABLED_ENV] = "true"
        published = event_publisher.publish_domain_event(
            "MissionCreated", source="check", aggregate_type="mission", aggregate_id="MISSION-ON",
        )
        assert published is not None
        assert event_publisher.EVENT_STORE.all() == [published]
        assert received == [published]
        assert len(event_publisher.COMPANY_BRAIN.timeline()) == 1
    finally:
        event_publisher.EVENT_STORE = original_store
        event_publisher.EVENT_BUS = original_bus
        event_publisher.COMPANY_BRAIN = original_brain
        if original_setting is None:
            os.environ.pop(event_publisher.EVENTS_ENABLED_ENV, None)
        else:
            os.environ[event_publisher.EVENTS_ENABLED_ENV] = original_setting


def _assert_neutral_event_sink() -> None:
    class RecordingSink:
        def __init__(self) -> None:
            self.events = []

        def emit(self, event_type: str, **fields: object) -> None:
            self.events.append({"event_type": event_type, **fields})

    reset_event_sink()
    emit_domain_event(
        "MissionCreated", source="check", aggregate_type="mission", aggregate_id="MISSION-NOOP",
    )
    sink = RecordingSink()
    set_event_sink(sink)
    try:
        emit_domain_event(
            "MissionCreated", source="check", aggregate_type="mission", aggregate_id="MISSION-INJECTED",
        )
        assert len(sink.events) == 1
        assert sink.events[0]["aggregate_id"] == "MISSION-INJECTED"
    finally:
        reset_event_sink()

    class FailingSink:
        def emit(self, event_type: str, **fields: object) -> None:
            raise RuntimeError("subscriber unavailable")

    set_event_sink(FailingSink())
    try:
        emit_domain_event(
            "MissionCreated", source="check", aggregate_type="mission", aggregate_id="MISSION-ISOLATED",
        )
    finally:
        reset_event_sink()

    concurrent_sink = RecordingSink()
    set_event_sink(concurrent_sink)
    try:
        threads = [
            Thread(
                target=emit_domain_event,
                kwargs={
                    "event_type": "MissionAdvanced", "source": "check",
                    "aggregate_type": "mission", "aggregate_id": "MISSION-{}".format(index),
                },
            )
            for index in range(20)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        assert len(concurrent_sink.events) == 20
    finally:
        reset_event_sink()


def _assert_observational_layers(brain: CompanyBrain, events: list[object]) -> None:
    twin = DigitalTwin()
    snapshot = twin.replay(events).snapshot()  # type: ignore[arg-type]
    assert snapshot["missions"]["MISSION-1"]["status"] == "active"  # type: ignore[index]
    assert snapshot["missions"]["MISSION-1"]["title"] == "Build company memory"  # type: ignore[index]

    simulation = SimulationEngine(brain, twin)
    session = simulation.create_session("capacity scenario", {"capacity": "constrained"})
    result = simulation.run(session)
    assert result["production_mutated"] is False
    assert simulation.predict().status == "not_implemented"

    council = ExecutiveCouncil(brain, twin, simulation)
    consultation = council.consult("Review the mission")
    assert consultation["autonomous_reasoning"] is False
    assert len(consultation["advice"]) == 4
    assert all(member.company_brain is brain for member in council.members)


def main() -> None:
    _assert_immutable()
    brain, events = _assert_append_only_and_replay()
    _assert_optional_publishing()
    _assert_neutral_event_sink()
    _assert_observational_layers(brain, events)
    print("company brain foundation check: PASS")


if __name__ == "__main__":
    main()
