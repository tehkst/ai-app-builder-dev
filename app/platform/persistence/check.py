from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.core.database_urls import normalize_async_database_url, normalize_sync_database_url
from app.platform.operating_console.mission_run_service import accept_mission_run
from app.platform.operating_console import mission_run_service
from app.platform.persistence import database as platform_database
from app.core.environment import classify_environment
from app.platform.persistence.readiness import database_infrastructure_lifecycle_evidence, inspect_platform_persistence_readiness, resolve_platform_database_url


BASE_URL = "postgresql://ai_factory_app:redacted@/ai_software_factory?host=/cloudsql/project:region:instance"


def main() -> None:
    assert normalize_async_database_url(BASE_URL).startswith("postgresql+asyncpg://")
    assert normalize_sync_database_url(BASE_URL).startswith("postgresql+psycopg2://")
    assert normalize_sync_database_url(normalize_async_database_url(BASE_URL)).startswith("postgresql+psycopg2://")
    assert normalize_async_database_url("sqlite:///./app.db") == "sqlite+aiosqlite:///./app.db"
    assert normalize_sync_database_url("sqlite+aiosqlite:///./platform.db") == "sqlite:///./platform.db"
    try:
        normalize_sync_database_url("mysql://user:password@host/db")
    except ValueError as exc:
        assert "Unsupported database URL scheme" in str(exc)
    else:
        raise AssertionError("unsupported scheme was accepted")

    local = inspect_platform_persistence_readiness({})
    assert classify_environment({"ENVIRONMENT": "production"}) == "production"
    assert classify_environment({"APP_ENV": "production"}) == "production"
    assert classify_environment({"K_SERVICE": "ai-software-factory-production"}) == "production"
    assert classify_environment({}) == "development"
    assert classify_environment({"K_SERVICE": "ai-software-factory-staging"}) == "staging"
    production_missing = inspect_platform_persistence_readiness({"ENVIRONMENT": "production"})
    cloud_run_production_missing = inspect_platform_persistence_readiness({"K_SERVICE": "ai-software-factory-production"})
    production_postgres = inspect_platform_persistence_readiness({"ENVIRONMENT": "production", "DATABASE_URL": BASE_URL})
    override_url, override_source = resolve_platform_database_url({"DATABASE_URL": BASE_URL, "PLATFORM_DATABASE_URL": BASE_URL})
    assert local["mode"] == "local_sqlite" and local["durable_runtime_available"] is True
    assert production_missing["production_safe"] is False and production_missing["durable_runtime_available"] is False
    assert production_postgres["mode"] == "shared_transactional" and production_postgres["cross_instance_coordination"] == "supported"
    assert production_postgres["commissioned"] is False and production_postgres["configuration_source"] == "DATABASE_URL"
    assert cloud_run_production_missing["durable_runtime_available"] is False
    assert production_postgres["connection_verified"] is False and production_postgres["active"] is False
    assert override_source == "PLATFORM_DATABASE_URL" and override_url.startswith("postgresql+psycopg2://")
    assert "redacted" not in str(production_postgres) and "cloudsql" not in str(production_postgres).lower()
    assert mission_run_service.PlatformSessionLocal is platform_database.PlatformSessionLocal
    assert platform_database.DEFAULT_PLATFORM_DB_CONNECT_TIMEOUT_SECONDS == 5
    assert platform_database.platform_db_connect_timeout_seconds("9") == 9
    assert platform_database.platform_db_connect_timeout_seconds("invalid") == 5
    assert platform_database.platform_db_connect_timeout_seconds("0") == 5
    assert platform_database.platform_db_connect_timeout_seconds("999") == 5
    if platform_database.platform_engine.dialect.name == "postgresql":
        assert platform_database.connect_args["connect_timeout"] == platform_database.PLATFORM_DB_CONNECT_TIMEOUT_SECONDS
    successful_connection = MagicMock()
    successful_connect = MagicMock()
    successful_connect.__enter__.return_value = successful_connection
    with patch.object(platform_database.platform_engine, "connect", return_value=successful_connect):
        verified_local = platform_database.verify_platform_persistence_connection(local)
        verified_postgres = platform_database.verify_platform_persistence_connection(production_postgres)
    assert verified_local["connection_verified"] is True and verified_local["active"] is True
    assert verified_local["commissioned"] is False and verified_local["mode"] == "local_sqlite"
    assert verified_postgres["connection_verified"] is True and verified_postgres["active"] is True
    assert verified_postgres["commissioned"] is True and verified_postgres["production_safe"] is True
    assert verified_postgres["cross_instance_coordination"] == "supported"
    with patch.object(platform_database.platform_engine, "connect", side_effect=RuntimeError("bounded failure")):
        unavailable = platform_database.verify_platform_persistence_connection(production_postgres)
    assert unavailable["connection_verified"] is False and unavailable["durable_runtime_available"] is False
    assert "bounded failure" not in str(unavailable)
    assert not any(term in str(unavailable).lower() for term in ("password", "username", "socket", "host="))

    evidence = database_infrastructure_lifecycle_evidence(production_postgres)
    historical = evidence["reported_commissioning_evidence"]
    assert historical["evidence_kind"] == "reported_historical" and historical["live_verification"] is False
    assert evidence["current_persistence_readiness"]["status"] == "NOT_VERIFIED"
    assert evidence["current_persistence_readiness"]["historical_claims_sufficient"] is False

    context = {"mission_id": "MISSION-PERSISTENCE-CHECK", "action_context_id": "ACTION-PERSISTENCE-CHECK"}
    with patch("app.platform.operating_console.mission_run_service.inspect_platform_persistence_readiness", return_value=production_missing), patch("app.platform.operating_console.mission_run_service._persist") as persist, patch("app.platform.operating_console.mission_run_service._enqueue") as enqueue, patch("app.platform.operating_console.mission_run_service._activate_canonical_worker") as worker:
        blocked = accept_mission_run(context=context, signature="signature", approval={"status": "approved"}, token="not-persisted")
    assert blocked["status"] == "blocked" and blocked["error"]["classification"] == "platform_persistence_unavailable"
    persist.assert_not_called()
    enqueue.assert_not_called()
    worker.assert_not_called()

    existing = {"found": True, "workflow_run_id": "MISSION-RUN-EXISTING", "mission_id": "MISSION-PERSISTENCE-CHECK", "current_stage": "change_set_ready", "steps": []}
    shared_unverified = dict(production_postgres)
    with patch("app.platform.operating_console.mission_run_service.inspect_platform_persistence_readiness", return_value=shared_unverified), patch("app.platform.operating_console.mission_run_service.load_mission_run", return_value=existing), patch("app.platform.operating_console.mission_run_service.verify_platform_persistence_connection", side_effect=AssertionError("probe must not hide existing run")):
        observed = accept_mission_run(context=context, signature="signature", approval={"status": "approved"}, token="session-token")
    assert observed["reused"] is True and observed["workflow_run_id"] == "MISSION-RUN-EXISTING"
    print("shared platform persistence URL and readiness contract ok")


if __name__ == "__main__":
    main()
