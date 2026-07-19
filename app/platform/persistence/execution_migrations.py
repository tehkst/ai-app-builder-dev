from __future__ import annotations

from sqlalchemy import Column, DateTime, MetaData, String, Table, Text, inspect, text

from app.platform.persistence.database import platform_engine


MIGRATION_ID = "20260719_01_platform_execution_layer"
ARTIFACT_CONTENT_MIGRATION_ID = "20260719_02_workspace_artifact_content"


def run_execution_layer_migrations() -> None:
    metadata = MetaData()
    migrations = Table(
        "platform_schema_migrations", metadata,
        Column("migration_id", String, primary_key=True),
        Column("applied_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    )
    from app.platform.persistence.models import (
        PlatformExecutionEvidence, PlatformExecutionWorkspace,
        PlatformGovernanceApproval, PlatformWorkspaceArtifact,
    )
    tables = [
        PlatformExecutionWorkspace.__table__, PlatformGovernanceApproval.__table__,
        PlatformExecutionEvidence.__table__, PlatformWorkspaceArtifact.__table__,
    ]
    with platform_engine.begin() as connection:
        if platform_engine.dialect.name == "postgresql":
            connection.execute(text("SELECT pg_advisory_xact_lock(85787156521)"))
        migrations.create(connection, checkfirst=True)
        applied = connection.execute(
            migrations.select().where(migrations.c.migration_id == MIGRATION_ID)
        ).first()
        if not applied:
            for table in tables:
                table.create(connection, checkfirst=True)
            connection.execute(migrations.insert().values(migration_id=MIGRATION_ID))
        artifact_applied = connection.execute(
            migrations.select().where(migrations.c.migration_id == ARTIFACT_CONTENT_MIGRATION_ID)
        ).first()
        if not artifact_applied:
            columns = {column["name"] for column in inspect(connection).get_columns("platform_workspace_artifacts")}
            if "content_base64" not in columns:
                connection.execute(text("ALTER TABLE platform_workspace_artifacts ADD COLUMN content_base64 TEXT"))
            connection.execute(migrations.insert().values(migration_id=ARTIFACT_CONTENT_MIGRATION_ID))


def execution_schema_status() -> dict:
    required = {
        "platform_execution_workspaces", "platform_governance_approvals",
        "platform_execution_evidence", "platform_workspace_artifacts",
    }
    present = set(inspect(platform_engine).get_table_names())
    return {"implemented": True, "configured": required.issubset(present), "tables": sorted(required & present)}
