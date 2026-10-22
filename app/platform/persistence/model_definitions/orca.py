"""Orca missions in the platform database (step 5b): the full mission state, plus a short live
activity feed (what each employee is doing right now)."""
from app.platform.persistence.model_definitions.base import Boolean, Column, DateTime, Integer, PlatformBase, String, Text, utc_now


class PlatformOrcaMission(PlatformBase):
    __tablename__ = "platform_orca_missions"

    id = Column(Integer, primary_key=True, index=True)
    mission_id = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, index=True, nullable=False)
    goal = Column(Text, nullable=False)
    client_id = Column(String, index=True, nullable=True)  # client missions only
    sandboxed = Column(Boolean, default=False, nullable=False)
    data_json = Column(Text, nullable=False)  # the whole Mission (models.Mission.to_dict)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)


class PlatformOrcaActivity(PlatformBase):
    """One line of live progress ("Builder: writing greet.py"). Kept short per mission."""
    __tablename__ = "platform_orca_activity"

    id = Column(Integer, primary_key=True, index=True)
    mission_id = Column(String, index=True, nullable=False)
    employee = Column(String, nullable=False)
    kind = Column(String, nullable=False)  # started | thinking | read | write | command | check | finished
    detail = Column(String, nullable=False)
    at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
