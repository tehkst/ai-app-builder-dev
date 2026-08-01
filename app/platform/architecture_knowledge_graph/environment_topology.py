from __future__ import annotations

"""Declared source of truth for per-environment deploy topology.

This is the registry that did not exist before 2026-08-01: every environment's Cloud Run
service, Cloud SQL connection, database, and DATABASE_URL secret name, hand-verified against
live GCP state. `environment_topology_check.py` asserts internal consistency (no two
environments may share a database/secret/service name) with zero GCP credentials.
`infrastructure_projection.py` compares this declaration against live `gcloud` output to detect
drift. `platform-deploy.yml` must reference these same values - keep them in sync by hand until
the workflow can source them directly (GitHub Actions cannot import Python).
"""

GCP_PROJECT_ID = "ai-software-factory-500910"
GCP_REGION = "asia-southeast1"

ENVIRONMENTS = {
    "production": {
        "cloud_run_service": "ai-software-factory-production",
        "cloud_sql_instance": "ai-factory-db",
        "cloud_sql_connection_name": "%s:%s:ai-factory-db" % (GCP_PROJECT_ID, GCP_REGION),
        "cloud_sql_database": "ai_software_factory",
        "database_secret": "ai-software-factory-production-database-url",
    },
    "staging": {
        "cloud_run_service": "ai-software-factory-staging",
        "cloud_sql_instance": "ai-factory-db",
        "cloud_sql_connection_name": "%s:%s:ai-factory-db" % (GCP_PROJECT_ID, GCP_REGION),
        "cloud_sql_database": "ai_software_factory_nonprod",
        "database_secret": "ai-software-factory-nonprod-database-url",
    },
    "dev": {
        "cloud_run_service": "ai-software-factory-dev",
        "cloud_sql_instance": "ai-factory-db",
        "cloud_sql_connection_name": "%s:%s:ai-factory-db" % (GCP_PROJECT_ID, GCP_REGION),
        "cloud_sql_database": "ai_software_factory_nonprod",
        "database_secret": "ai-software-factory-nonprod-database-url",
    },
}
