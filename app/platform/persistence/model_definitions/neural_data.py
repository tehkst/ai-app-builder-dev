from __future__ import annotations

import os

from sqlalchemy import Index, JSON
from sqlalchemy.dialects.postgresql import JSONB

try:
    from pgvector.sqlalchemy import Vector
except Exception:  # pragma: no cover - pgvector is optional for sqlite/local dev.
    Vector = None

from app.platform.persistence.model_definitions.base import Boolean, Column, DateTime, Integer, PlatformBase, String, Text, utc_now


def _json_document_type():
    return JSON().with_variant(JSONB, "postgresql")


def _vector_type(dimensions: int = 1536):
    """Return a safe ORM type for embedding storage.

    Production startup still calls SQLAlchemy create_all(). If pgvector is present in
    Python but the PostgreSQL extension has not been enabled yet, a vector column can
    make startup fail before /health becomes available. Keep ORM startup safe by using
    Text unless explicitly enabled. The production SQL migration remains the source of
    truth for true vector(1536) + HNSW indexes.
    """

    enable_pgvector_orm = os.getenv("PLATFORM_ENABLE_PGVECTOR_ORM", "false").lower() == "true"
    if Vector is None or not enable_pgvector_orm:
        return Text
    return Vector(dimensions)


class PlatformNeuralDocument(PlatformBase):
    """JSONB/document substrate for unstructured agent, compiler, and system state data.

    This is additive to the existing JSON-string fields. It lets production PostgreSQL
    use JSONB + GIN while sqlite/local dev keeps working with SQLAlchemy JSON.
    """

    __tablename__ = "platform_neural_documents"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String, unique=True, index=True, nullable=False)

    tenant_id = Column(String, index=True, nullable=True)
    workspace_id = Column(String, index=True, nullable=True)
    project_id = Column(String, index=True, nullable=True)
    workflow_run_id = Column(String, index=True, nullable=True)
    source_type = Column(String, index=True, nullable=False)
    source_id = Column(String, index=True, nullable=False)

    document_kind = Column(String, index=True, nullable=False)
    document_hash = Column(String, index=True, nullable=False)
    content_text = Column(Text, default="", nullable=False)
    payload = Column(_json_document_type(), default=dict, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_platform_neural_documents_source", "source_type", "source_id"),
        Index("ix_platform_neural_documents_workflow_kind", "workflow_run_id", "document_kind"),
    )


class PlatformSemanticEmbedding(PlatformBase):
    """AI-native semantic index row for source artifacts.

    The ORM column defaults to Text for safe Railway startup. Run the explicit
    PostgreSQL migration to create true vector(1536) + HNSW infrastructure.
    """

    __tablename__ = "platform_semantic_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    embedding_id = Column(String, unique=True, index=True, nullable=False)

    tenant_id = Column(String, index=True, nullable=True)
    workspace_id = Column(String, index=True, nullable=True)
    project_id = Column(String, index=True, nullable=True)
    workflow_run_id = Column(String, index=True, nullable=True)
    source_type = Column(String, index=True, nullable=False)
    source_id = Column(String, index=True, nullable=False)

    embedding_model = Column(String, index=True, nullable=False)
    embedding_dimensions = Column(Integer, default=1536, nullable=False)
    embedding_vector = Column(_vector_type(1536), nullable=False)
    metadata_payload = Column(_json_document_type(), default=dict, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_platform_semantic_embeddings_source", "source_type", "source_id"),
        Index("ix_platform_semantic_embeddings_workflow", "workflow_run_id"),
    )


class PlatformAstGraphNode(PlatformBase):
    """Graph substrate for code/module AST and dependency semantics."""

    __tablename__ = "platform_ast_graph_nodes"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(String, unique=True, index=True, nullable=False)

    tenant_id = Column(String, index=True, nullable=True)
    workspace_id = Column(String, index=True, nullable=True)
    project_id = Column(String, index=True, nullable=True)
    workflow_run_id = Column(String, index=True, nullable=True)
    source_file_id = Column(String, index=True, nullable=True)

    node_type = Column(String, index=True, nullable=False)
    symbol_name = Column(String, index=True, nullable=True)
    language = Column(String, index=True, nullable=True)
    span_start = Column(Integer, nullable=True)
    span_end = Column(Integer, nullable=True)
    attributes = Column(_json_document_type(), default=dict, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_platform_ast_graph_nodes_file_type", "source_file_id", "node_type"),
        Index("ix_platform_ast_graph_nodes_symbol", "symbol_name"),
    )


class PlatformAstGraphEdge(PlatformBase):
    """Directed graph edge for AST/dependency relationships."""

    __tablename__ = "platform_ast_graph_edges"

    id = Column(Integer, primary_key=True, index=True)
    edge_id = Column(String, unique=True, index=True, nullable=False)

    tenant_id = Column(String, index=True, nullable=True)
    workspace_id = Column(String, index=True, nullable=True)
    project_id = Column(String, index=True, nullable=True)
    workflow_run_id = Column(String, index=True, nullable=True)

    from_node_id = Column(String, index=True, nullable=False)
    to_node_id = Column(String, index=True, nullable=False)
    edge_type = Column(String, index=True, nullable=False)
    attributes = Column(_json_document_type(), default=dict, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_platform_ast_graph_edges_from_type", "from_node_id", "edge_type"),
        Index("ix_platform_ast_graph_edges_to_type", "to_node_id", "edge_type"),
    )


class PlatformIngestionEventBuffer(PlatformBase):
    """Write-behind buffer for bursty agent/compiler/runtime events."""

    __tablename__ = "platform_ingestion_event_buffer"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, index=True, nullable=False)

    tenant_id = Column(String, index=True, nullable=True)
    workspace_id = Column(String, index=True, nullable=True)
    project_id = Column(String, index=True, nullable=True)
    workflow_run_id = Column(String, index=True, nullable=True)
    source_type = Column(String, index=True, nullable=False)
    source_id = Column(String, index=True, nullable=True)

    event_kind = Column(String, index=True, nullable=False)
    ingestion_status = Column(String, default="queued", index=True, nullable=False)
    priority = Column(Integer, default=100, index=True, nullable=False)
    payload = Column(_json_document_type(), default=dict, nullable=False)
    error_message = Column(Text, default="", nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    processed = Column(Boolean, default=False, index=True, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_platform_ingestion_buffer_status_priority", "ingestion_status", "priority"),
        Index("ix_platform_ingestion_buffer_workflow_kind", "workflow_run_id", "event_kind"),
    )
