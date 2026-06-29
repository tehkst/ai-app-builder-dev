from __future__ import annotations

from pathlib import Path

REQUIRED_PATHS = [
    "infra/README.md",
    "infra/bootstrap/README.md",
    "infra/terraform/shared/variables.tf",
    "infra/terraform/shared/versions.tf",
    "infra/terraform/environments/dev/main.tf",
    "infra/terraform/environments/staging/main.tf",
    "infra/terraform/environments/production/main.tf",
    "infra/terraform/modules/cloud_run/README.md",
    "infra/terraform/modules/cloud_sql/README.md",
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
    for env in ["dev", "staging", "production"]:
        content = Path(f"infra/terraform/environments/{env}/main.tf").read_text(encoding="utf-8")
        assert f'environment = "{env}"' in content
    print("P1.1 GCP FOUNDATION CHECK PASSED")


if __name__ == "__main__":
    main()
