from __future__ import annotations

from pathlib import Path

CORE_CHECKS = [
    "app/platform/gcp/check.py",
    "app/platform/gcp/ops_check.py",
    "app/platform/mission_control/check.py",
    "app/platform/executive_office/check.py",
    "app/platform/ai_workforce/check.py",
    "infra/scripts/validate.sh",
    "infra/scripts/plan.sh",
    "infra/scripts/apply.sh",
]

MODULES = [
    "cloud_run",
    "cloud_sql",
    "identity",
    "images",
    "networking",
    "ops",
    "secret_manager",
]

ENVIRONMENTS = ["dev", "staging", "production"]


def require(path: str) -> None:
    assert Path(path).exists(), f"Missing required path: {path}"


def require_text(path: str, text: str) -> None:
    content = Path(path).read_text(encoding="utf-8")
    assert text in content, f"Missing {text!r} in {path}"


def main() -> None:
    for path in CORE_CHECKS:
        require(path)

    for module in MODULES:
        require(f"infra/terraform/modules/{module}/main.tf")
        require(f"infra/terraform/modules/{module}/variables.tf")
        require(f"infra/terraform/modules/{module}/outputs.tf")

    for environment in ENVIRONMENTS:
        root = f"infra/terraform/environments/{environment}/main.tf"
        require(root)
        require_text(root, f'environment = "{environment}"')
        require_text(root, 'module "cloud_run"')
        require_text(root, 'module "cloud_sql"')
        require_text(root, 'module "secret_manager"')
        require_text(root, 'module "images"')

    print("P2.0 WORKFORCE READINESS CHECK PASSED")


if __name__ == "__main__":
    main()
