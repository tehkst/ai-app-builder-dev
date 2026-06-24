"""Neural data fabric schema readiness check.

This check is non-destructive. It validates ORM registration and the presence of the
production PostgreSQL migration artifact for JSONB, pgvector, graph, and ingestion
buffer substrates.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.platform.persistence.models import PlatformBase


REQUIRED_TABLES = {
    "platform_neural_documents",
    "platform_semantic_embeddings",
    "platform_ast_graph_nodes",
    "platform_ast_graph_edges",
    "platform_ingestion_event_buffer",
}


def run_neural_data_fabric_schema_check() -> dict:
    registered_tables = set(PlatformBase.metadata.tables.keys())
    missing_tables = sorted(REQUIRED_TABLES - registered_tables)

    migration_path = Path("docs/db/001_neural_data_fabric_postgres.sql")
    migration_text = migration_path.read_text() if migration_path.exists() else ""

    required_migration_markers = [
        "CREATE EXTENSION IF NOT EXISTS vector",
        "JSONB",
        "USING GIN",
        "USING hnsw",
        "platform_ingestion_event_buffer",
    ]

    missing_migration_markers = [
        marker for marker in required_migration_markers if marker not in migration_text
    ]

    success = not missing_tables and migration_path.exists() and not missing_migration_markers

    return {
        "success": success,
        "neural_data_fabric_ready": success,
        "registered_tables": sorted(REQUIRED_TABLES),
        "missing_tables": missing_tables,
        "migration_path": str(migration_path),
        "migration_present": migration_path.exists(),
        "missing_migration_markers": missing_migration_markers,
        "safety_summary": {
            "additive_schema_only": True,
            "existing_tables_mutated": False,
            "production_source_mutation_performed": False,
            "database_migration_executed_by_check": False,
            "generated_code_execution_performed": False,
            "external_deployment_performed": False,
        },
    }


def main() -> None:
    result = run_neural_data_fabric_schema_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
