from __future__ import annotations

from pathlib import Path

CORE_CHECKS = [
    "app/platform/gcp/check.py",
    "app/platform/mission_control/check.py",
    "app/platform/executive_office/check.py",
    "app/platform/ai_workforce/check.py",
    "app/platform/knowledge_vault/check.py",
    "app/platform/ui/check.py",
    "app/platform/api_contract.py",
    "infra/scripts/validate.sh",
    ".github/workflows/platform-deploy.yml",
]


def require(path: str) -> None:
    assert Path(path).exists(), f"Missing required path: {path}"


def main() -> None:
    for path in CORE_CHECKS:
        require(path)

    print("P3.1 MISSION CONTROL API CONTRACT READINESS CHECK PASSED")


if __name__ == "__main__":
    main()
