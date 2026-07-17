from __future__ import annotations

import os

from app.platform.company_brain import event_publisher
from app.platform.company_brain.event_bus import InProcessEventBus
from app.platform.company_brain.event_store import ImmutableEventStore
from app.platform.events.event_sink import emit_domain_event, reset_event_sink
from app.platform.server import configure_company_brain_event_sink, reset_company_brain_event_sink


def _reset_company_brain_projection() -> None:
    from app.platform.company_brain.company_brain import CompanyBrain

    event_publisher.EVENT_STORE = ImmutableEventStore()
    event_publisher.EVENT_BUS = InProcessEventBus()
    event_publisher.COMPANY_BRAIN = CompanyBrain(event_publisher.EVENT_STORE)
    event_publisher.EVENT_BUS.subscribe("*", event_publisher.COMPANY_BRAIN.project)


def main() -> None:
    original_setting = os.environ.get(event_publisher.EVENTS_ENABLED_ENV)
    try:
        _reset_company_brain_projection()
        os.environ[event_publisher.EVENTS_ENABLED_ENV] = "false"
        configure_company_brain_event_sink()
        emit_domain_event(
            "MissionCreated", source="check", aggregate_type="mission", aggregate_id="MISSION-DISABLED",
        )
        assert event_publisher.EVENT_STORE.all() == []

        os.environ[event_publisher.EVENTS_ENABLED_ENV] = "true"
        configure_company_brain_event_sink()
        emit_domain_event(
            "MissionCreated", source="check", aggregate_type="mission", aggregate_id="MISSION-ENABLED",
        )
        assert len(event_publisher.EVENT_STORE.all()) == 1
        assert len(event_publisher.COMPANY_BRAIN.timeline()) == 1
        reset_company_brain_event_sink()
        emit_domain_event(
            "MissionCreated", source="check", aggregate_type="mission", aggregate_id="MISSION-AFTER-SHUTDOWN",
        )
        assert len(event_publisher.EVENT_STORE.all()) == 1
    finally:
        reset_event_sink()
        if original_setting is None:
            os.environ.pop(event_publisher.EVENTS_ENABLED_ENV, None)
        else:
            os.environ[event_publisher.EVENTS_ENABLED_ENV] = original_setting

    print("company brain startup injection check: PASS")


if __name__ == "__main__":
    main()
