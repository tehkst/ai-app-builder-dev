-- 001_neural_data_fabric_postgres.sql
-- Additive PostgreSQL neural data fabric foundation.
-- This migration does not mutate existing production tables.

BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS platform_neural_documents (
    id BIGSERIAL PRIMARY KEY,
    document_id TEXT NOT NULL UNIQUE,
    tenant_id TEXT,
    workspace_id TEXT,
    project_id TEXT,
    workflow_run_id TEXT,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    document_kind TEXT NOT NULL,
    document_hash TEXT NOT NULL,
    content_text TEXT NOT NULL DEFAULT '',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform_semantic_embeddings (
    id BIGSERIAL PRIMARY KEY,
    embedding_id TEXT NOT NULL UNIQUE,
    tenant_id TEXT,
    workspace_id TEXT,
    project_id TEXT,
    workflow_run_id TEXT,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding_dimensions INTEGER NOT NULL DEFAULT 1536,
    embedding_vector vector(1536) NOT NULL,
    metadata_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform_ast_graph_nodes (
    id BIGSERIAL PRIMARY KEY,
    node_id TEXT NOT NULL UNIQUE,
    tenant_id TEXT,
    workspace_id TEXT,
    project_id TEXT,
    workflow_run_id TEXT,
    source_file_id TEXT,
    node_type TEXT NOT NULL,
    symbol_name TEXT,
    language TEXT,
    span_start INTEGER,
    span_end INTEGER,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform_ast_graph_edges (
    id BIGSERIAL PRIMARY KEY,
    edge_id TEXT NOT NULL UNIQUE,
    tenant_id TEXT,
    workspace_id TEXT,
    project_id TEXT,
    workflow_run_id TEXT,
    from_node_id TEXT NOT NULL,
    to_node_id TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform_ingestion_event_buffer (
    id BIGSERIAL PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE,
    tenant_id TEXT,
    workspace_id TEXT,
    project_id TEXT,
    workflow_run_id TEXT,
    source_type TEXT NOT NULL,
    source_id TEXT,
    event_kind TEXT NOT NULL,
    ingestion_status TEXT NOT NULL DEFAULT 'queued',
    priority INTEGER NOT NULL DEFAULT 100,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_message TEXT NOT NULL DEFAULT '',
    retry_count INTEGER NOT NULL DEFAULT 0,
    processed BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_platform_neural_documents_source
    ON platform_neural_documents (source_type, source_id);

CREATE INDEX IF NOT EXISTS ix_platform_neural_documents_workflow_kind
    ON platform_neural_documents (workflow_run_id, document_kind);

CREATE INDEX IF NOT EXISTS ix_platform_neural_documents_payload_gin
    ON platform_neural_documents USING GIN (payload jsonb_path_ops);

CREATE INDEX IF NOT EXISTS ix_platform_semantic_embeddings_source
    ON platform_semantic_embeddings (source_type, source_id);

CREATE INDEX IF NOT EXISTS ix_platform_semantic_embeddings_workflow
    ON platform_semantic_embeddings (workflow_run_id);

CREATE INDEX IF NOT EXISTS ix_platform_semantic_embeddings_metadata_gin
    ON platform_semantic_embeddings USING GIN (metadata_payload jsonb_path_ops);

CREATE INDEX IF NOT EXISTS ix_platform_semantic_embeddings_vector_hnsw
    ON platform_semantic_embeddings USING hnsw (embedding_vector vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS ix_platform_ast_graph_nodes_file_type
    ON platform_ast_graph_nodes (source_file_id, node_type);

CREATE INDEX IF NOT EXISTS ix_platform_ast_graph_nodes_symbol
    ON platform_ast_graph_nodes (symbol_name);

CREATE INDEX IF NOT EXISTS ix_platform_ast_graph_nodes_attributes_gin
    ON platform_ast_graph_nodes USING GIN (attributes jsonb_path_ops);

CREATE INDEX IF NOT EXISTS ix_platform_ast_graph_edges_from_type
    ON platform_ast_graph_edges (from_node_id, edge_type);

CREATE INDEX IF NOT EXISTS ix_platform_ast_graph_edges_to_type
    ON platform_ast_graph_edges (to_node_id, edge_type);

CREATE INDEX IF NOT EXISTS ix_platform_ast_graph_edges_attributes_gin
    ON platform_ast_graph_edges USING GIN (attributes jsonb_path_ops);

CREATE INDEX IF NOT EXISTS ix_platform_ingestion_buffer_status_priority
    ON platform_ingestion_event_buffer (ingestion_status, priority, created_at);

CREATE INDEX IF NOT EXISTS ix_platform_ingestion_buffer_workflow_kind
    ON platform_ingestion_event_buffer (workflow_run_id, event_kind);

CREATE INDEX IF NOT EXISTS ix_platform_ingestion_buffer_payload_gin
    ON platform_ingestion_event_buffer USING GIN (payload jsonb_path_ops);

COMMIT;
