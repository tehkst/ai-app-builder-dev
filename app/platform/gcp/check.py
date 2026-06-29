from __future__ import annotations

from pathlib import Path

REQUIRED_PATHS = [
    "Dockerfile",
    "infra/README.md",
    "infra/bootstrap/README.md",
    "infra/terraform/shared/variables.tf",
    "infra/terraform/shared/versions.tf",
    "infra/terraform/environments/dev/main.tf",
    "infra/terraform/environments/staging/main.tf",
    "infra/terraform/environments/production/main.tf",
    "infra/terraform/modules/cloud_run/README.md",
    "infra/terraform/modules/cloud_run/main.tf",
    "infra/terraform/modules/cloud_run/variables.tf",
    "infra/terraform/modules/cloud_run/outputs.tf",
    "infra/terraform/modules/cloud_sql/README.md",
    "infra/terraform/modules/cloud_sql/main.tf",
    "infra/terraform/modules/cloud_sql/variables.tf",
    "infra/terraform/modules/cloud_sql/outputs.tf",
    "infra/terraform/modules/artifact_registry/README.md",
    "infra/terraform/modules/secret_manager/README.md",
    "infra/terraform/modules/redis/README.md",
    "infra/terraform/modules/pubsub/README.md",
    "infra/terraform/modules/storage/README.md",
    "infra/terraform/modules/monitoring/README.md",
    "infra/terraform/modules/networking/README.md",
    "infra/scripts/bootstrap.sh",
    "infra/scripts/plan.sh",
    "infra/scripts/apply.sh",
    "infra/scripts/destroy.sh",
    "infra/scripts/validate.sh",
]


def main() -> None:
    missing = [path for path in REQUIRED_PATHS if not Path(path).exists()]
    assert not missing, f"Missing GCP foundation paths: {missing}"
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    assert "PORT=8080" in dockerfile
    assert "EXPOSE 8080" in dockerfile
    run_module = Path("infra/terraform/modules/cloud_run/main.tf").read_text(encoding="utf-8")
    assert "google_cloud_run_v2_service" in run_module
    assert "startup_probe" in run_module
    assert "liveness_probe" in run_module
    sql_module = Path("infra/terraform/modules/cloud_sql/main.tf").read_text(encoding="utf-8")
    assert "google_sql_database_instance" in sql_module
    assert "point_in_time_recovery_enabled" in sql_module
    assert "google_sql_database" in sql_module
    for env in ["dev", "staging", "production"]:
        content = Path(f"infra/terraform/environments/{env}/main.tf").read_text(encoding="utf-8")
        assert f'environment = "{env}"' in content
        assert 'module "cloud_run"' in content
        assert 'module "cloud_sql"' in content
        assert "CLOUD_SQL_CONNECTION_NAME" in content
    print("P1.3 CLOUD SQL FOUNDATION CHECK PASSED")


if __name__ == "__main__":
    main()
