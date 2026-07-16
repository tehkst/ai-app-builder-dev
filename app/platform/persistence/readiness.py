from __future__ import annotations

import os
from typing import Mapping

from app.core.database_urls import database_family, normalize_sync_database_url
from app.core.environment import classify_environment


DEFAULT_PLATFORM_DATABASE_URL = "sqlite:///./platform.db"


def resolve_platform_database_url(environment: Mapping[str, str] | None = None) -> tuple[str, str]:
    values = environment if environment is not None else os.environ
    if values.get("PLATFORM_DATABASE_URL"):
        return normalize_sync_database_url(values["PLATFORM_DATABASE_URL"]), "PLATFORM_DATABASE_URL"
    if values.get("DATABASE_URL"):
        return normalize_sync_database_url(values["DATABASE_URL"]), "DATABASE_URL"
    return DEFAULT_PLATFORM_DATABASE_URL, "default"


def inspect_platform_persistence_readiness(environment: Mapping[str, str] | None = None) -> dict[str, object]:
    values = environment if environment is not None else os.environ
    database_url, source = resolve_platform_database_url(values)
    family = database_family(database_url)
    environment_class = classify_environment(values)
    production = environment_class == "production"
    shared = family == "postgresql"
    reasons: list[str] = []
    if production and not shared:
        reasons.append("Production durable runtime requires shared transactional PostgreSQL persistence.")
    if source == "default":
        reasons.append("No explicit platform or application database configuration is present.")
    if family == "unknown":
        reasons.append("The configured database family is unsupported or unknown.")
    return {
        "mode": "shared_transactional" if shared else "local_sqlite" if family == "sqlite" else "unknown",
        "production_safe": shared if production else family in {"postgresql", "sqlite"},
        "database_family": family,
        "configuration_source": source,
        "cross_instance_coordination": "supported" if shared else "unsupported",
        "durable_runtime_available": shared or (not production and family == "sqlite"),
        "commissioned": False,
        "connection_verified": False,
        "active": False,
        "environment_class": environment_class,
        "reasons": reasons,
        "sensitive_configuration_exposed": False,
    }


def build_platform_persistence_readiness() -> dict[str, object]:
    readiness = inspect_platform_persistence_readiness()
    if readiness["durable_runtime_available"]:
        from app.platform.persistence.database import verify_platform_persistence_connection

        readiness = verify_platform_persistence_connection(readiness)
    return {
        "status": "platform-persistence-readiness",
        "platform_persistence": readiness,
        "evidence": database_infrastructure_lifecycle_evidence(readiness),
    }


def database_infrastructure_lifecycle_evidence(readiness: Mapping[str, object] | None = None) -> dict[str, object]:
    configured = bool(readiness and readiness.get("configuration_source") != "default")
    verified = bool(readiness and readiness.get("connection_verified"))
    return {
        "reported_commissioning_evidence": {
            "evidence_kind": "reported_historical",
            "source": "founder-commissioning-evidence",
            "as_of": "2026-07-16",
            "live_verification": False,
            "states": {
                "cloud_sql": "PROVISIONED",
                "logical_database": "PROVISIONED",
                "database_secret": "PROVISIONED",
                "secret_runtime_access": "WIRED",
                "cloud_sql_attachment": "WIRED",
                "cloud_sql_client_role": "UNKNOWN",
            },
        },
        "runtime_configuration_evidence": {
            "evidence_kind": "current_process_configuration",
            "configuration_source": readiness.get("configuration_source") if readiness else "default",
            "database_family": readiness.get("database_family") if readiness else "unknown",
            "environment_class": readiness.get("environment_class") if readiness else "unknown",
            "configured": configured,
        },
        "runtime_connection_evidence": {
            "evidence_kind": "bounded_runtime_probe",
            "connection_verified": verified,
            "active": bool(readiness and readiness.get("active")),
            "failure_reasons": list(readiness.get("reasons") or []) if readiness else [],
        },
        "current_persistence_readiness": {
            "status": "VERIFIED" if verified else "NOT_VERIFIED",
            "derived_from_current_runtime_evidence": True,
            "historical_claims_sufficient": False,
        },
        "semantics": {
            "DEFINED": "Declared in repository configuration without commissioning evidence.",
            "PROVISIONED": "A live resource was reported as created and runnable.",
            "WIRED": "A required attachment or access binding was reported as configured.",
            "ACTIVE": "The application is configured to use the capability at runtime.",
            "VERIFIED": "A bounded runtime check proved the capability works.",
            "UNKNOWN": "Available evidence cannot establish the lifecycle state.",
        },
        "sensitive_configuration_exposed": False,
    }
