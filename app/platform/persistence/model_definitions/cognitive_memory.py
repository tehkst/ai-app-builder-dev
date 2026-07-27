from __future__ import annotations

from sqlalchemy import Index, UniqueConstraint

from app.platform.persistence.model_definitions.base import Column, DateTime, Integer, PlatformBase, String, Text, utc_now


class PlatformEntity(PlatformBase):
    """A canonical, named fact-graph node (person, agent, mission, decision, requirement, ...)."""

    __tablename__ = "platform_entities"

    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(String, unique=True, index=True, nullable=False)

    tenant_id = Column(String, index=True, nullable=True)
    name = Column(String, nullable=False)
    type = Column(String, index=True, nullable=False)
    canonical_key = Column(String, index=True, nullable=False)
    metadata_json = Column(Text, default="{}", nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("canonical_key", name="uq_platform_entity_canonical_key"),
        Index("ix_platform_entities_tenant_type", "tenant_id", "type"),
    )


class PlatformEdge(PlatformBase):
    """A directed, typed relationship between two PlatformEntity rows."""

    __tablename__ = "platform_edges"

    id = Column(Integer, primary_key=True, index=True)
    edge_id = Column(String, unique=True, index=True, nullable=False)

    tenant_id = Column(String, index=True, nullable=True)
    source_entity_id = Column(String, index=True, nullable=False)
    target_entity_id = Column(String, index=True, nullable=False)
    relationship = Column(String, index=True, nullable=False)
    metadata_json = Column(Text, default="{}", nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "source_entity_id", "target_entity_id", "relationship",
            name="uq_platform_edge_triple",
        ),
        Index("ix_platform_edges_source", "source_entity_id", "relationship"),
        Index("ix_platform_edges_target", "target_entity_id", "relationship"),
    )


class PlatformEpisode(PlatformBase):
    """A raw, timestamped record of something that happened - the recall/context substrate.

    Distinct from entities/edges: episodes are high-recall, embedding-searchable, and not
    treated as verified facts on their own. Only entities/edges are used for exact-match
    grounding; episodes support semantic recall and provide supporting evidence/citations.
    """

    __tablename__ = "platform_episodes"

    id = Column(Integer, primary_key=True, index=True)
    episode_id = Column(String, unique=True, index=True, nullable=False)

    tenant_id = Column(String, index=True, nullable=True)
    content = Column(Text, nullable=False)
    entity_references_json = Column(Text, default="[]", nullable=False)
    source_type = Column(String, index=True, nullable=False)
    source_id = Column(String, index=True, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_platform_episodes_tenant_source", "tenant_id", "source_type"),
    )
