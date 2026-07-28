from __future__ import annotations

from sqlalchemy import Column, DateTime, MetaData, String, Table, Text, inspect, text

from app.platform.persistence.database import platform_engine


MIGRATION_ID = "20260719_01_platform_execution_layer"
ARTIFACT_CONTENT_MIGRATION_ID = "20260719_02_workspace_artifact_content"
VALIDATION_MIGRATION_ID = "20260719_03_platform_validation_framework"
SCOPING_VERSIONING_MIGRATION_ID = "20260726_01_scoping_request_versioning"
RUNTIME_SETTINGS_MIGRATION_ID = "20260727_01_platform_runtime_settings"
FOUNDER_RESET_MIGRATION_ID = "20260727_02_platform_founder_reset_tokens"
COGNITIVE_MEMORY_MIGRATION_ID = "20260727_03_platform_cognitive_memory"
CREDENTIAL_VAULT_MIGRATION_ID = "20260728_01_platform_credential_vault"
REPO_IMPORT_MIGRATION_ID = "20260728_02_platform_repo_import"
UI_UX_PROPOSAL_MIGRATION_ID = "20260728_03_platform_ui_ux_proposal"


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
        PlatformValidationMission, PlatformValidationStep,
    )
    tables = [
        PlatformExecutionWorkspace.__table__, PlatformGovernanceApproval.__table__,
        PlatformExecutionEvidence.__table__, PlatformWorkspaceArtifact.__table__,
        PlatformValidationMission.__table__, PlatformValidationStep.__table__,
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
        validation_applied = connection.execute(
            migrations.select().where(migrations.c.migration_id == VALIDATION_MIGRATION_ID)
        ).first()
        if not validation_applied:
            PlatformValidationMission.__table__.create(connection, checkfirst=True)
            PlatformValidationStep.__table__.create(connection, checkfirst=True)
            connection.execute(migrations.insert().values(migration_id=VALIDATION_MIGRATION_ID))
        scoping_versioning_applied = connection.execute(
            migrations.select().where(migrations.c.migration_id == SCOPING_VERSIONING_MIGRATION_ID)
        ).first()
        if not scoping_versioning_applied:
            existing_tables = set(inspect(connection).get_table_names())
            if "platform_scoping_requests" in existing_tables:
                columns = {column["name"] for column in inspect(connection).get_columns("platform_scoping_requests")}
                if "request_kind" not in columns:
                    connection.execute(
                        text(
                            "ALTER TABLE platform_scoping_requests "
                            "ADD COLUMN request_kind VARCHAR NOT NULL DEFAULT 'platform_self_build'"
                        )
                    )
                if "version" not in columns:
                    connection.execute(
                        text("ALTER TABLE platform_scoping_requests ADD COLUMN version INTEGER NOT NULL DEFAULT 1")
                    )
                if "previous_scoping_request_id" not in columns:
                    connection.execute(
                        text("ALTER TABLE platform_scoping_requests ADD COLUMN previous_scoping_request_id VARCHAR")
                    )
                if "workflow_run_id" not in columns:
                    connection.execute(
                        text("ALTER TABLE platform_scoping_requests ADD COLUMN workflow_run_id VARCHAR")
                    )
                connection.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_platform_scoping_requests_request_kind "
                        "ON platform_scoping_requests (request_kind)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_platform_scoping_requests_version "
                        "ON platform_scoping_requests (version)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_platform_scoping_requests_previous_scoping_request_id "
                        "ON platform_scoping_requests (previous_scoping_request_id)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_platform_scoping_requests_workflow_run_id "
                        "ON platform_scoping_requests (workflow_run_id)"
                    )
                )
            connection.execute(migrations.insert().values(migration_id=SCOPING_VERSIONING_MIGRATION_ID))
        runtime_settings_applied = connection.execute(
            migrations.select().where(migrations.c.migration_id == RUNTIME_SETTINGS_MIGRATION_ID)
        ).first()
        if not runtime_settings_applied:
            from app.platform.persistence.models import PlatformRuntimeSetting

            PlatformRuntimeSetting.__table__.create(connection, checkfirst=True)
            connection.execute(migrations.insert().values(migration_id=RUNTIME_SETTINGS_MIGRATION_ID))
        founder_reset_applied = connection.execute(
            migrations.select().where(migrations.c.migration_id == FOUNDER_RESET_MIGRATION_ID)
        ).first()
        if not founder_reset_applied:
            from app.platform.persistence.models import PlatformFounderResetToken

            PlatformFounderResetToken.__table__.create(connection, checkfirst=True)
            connection.execute(migrations.insert().values(migration_id=FOUNDER_RESET_MIGRATION_ID))
        cognitive_memory_applied = connection.execute(
            migrations.select().where(migrations.c.migration_id == COGNITIVE_MEMORY_MIGRATION_ID)
        ).first()
        if not cognitive_memory_applied:
            from app.platform.persistence.models import PlatformEdge, PlatformEntity, PlatformEpisode

            PlatformEntity.__table__.create(connection, checkfirst=True)
            PlatformEdge.__table__.create(connection, checkfirst=True)
            PlatformEpisode.__table__.create(connection, checkfirst=True)
            connection.execute(migrations.insert().values(migration_id=COGNITIVE_MEMORY_MIGRATION_ID))
        credential_vault_applied = connection.execute(
            migrations.select().where(migrations.c.migration_id == CREDENTIAL_VAULT_MIGRATION_ID)
        ).first()
        if not credential_vault_applied:
            from app.platform.persistence.models import PlatformCredential

            PlatformCredential.__table__.create(connection, checkfirst=True)
            connection.execute(migrations.insert().values(migration_id=CREDENTIAL_VAULT_MIGRATION_ID))
        repo_import_applied = connection.execute(
            migrations.select().where(migrations.c.migration_id == REPO_IMPORT_MIGRATION_ID)
        ).first()
        if not repo_import_applied:
            from app.platform.persistence.models import PlatformImportedRepository

            PlatformImportedRepository.__table__.create(connection, checkfirst=True)
            connection.execute(migrations.insert().values(migration_id=REPO_IMPORT_MIGRATION_ID))
        ui_ux_proposal_applied = connection.execute(
            migrations.select().where(migrations.c.migration_id == UI_UX_PROPOSAL_MIGRATION_ID)
        ).first()
        if not ui_ux_proposal_applied:
            from app.platform.persistence.models import PlatformUiUxProposal

            PlatformUiUxProposal.__table__.create(connection, checkfirst=True)
            connection.execute(migrations.insert().values(migration_id=UI_UX_PROPOSAL_MIGRATION_ID))


def execution_schema_status() -> dict:
    required = {
        "platform_execution_workspaces", "platform_governance_approvals",
        "platform_execution_evidence", "platform_workspace_artifacts",
        "platform_validation_missions", "platform_validation_steps",
    }
    present = set(inspect(platform_engine).get_table_names())
    return {"implemented": True, "configured": required.issubset(present), "tables": sorted(required & present)}
