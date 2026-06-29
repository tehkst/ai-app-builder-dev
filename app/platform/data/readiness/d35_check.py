from __future__ import annotations

from pathlib import Path

REQUIRED_PATHS = [
    "app/platform/data/migrations/registry.py",
    "app/platform/data/migrations/migration_check.py",
    "app/platform/data/tenants/tenant_models.py",
    "app/platform/data/tenants/tenant_store.py",
    "app/platform/data/events/event_models.py",
    "app/platform/data/events/event_store.py",
    "docs/data/d3-4-data-safety.md",
    "app/platform/data/recovery/recovery_check.py",
]


def main() -> None:
    missing = [path for path in REQUIRED_PATHS if not Path(path).exists()]
    assert not missing, f"Missing D3 files: {missing}"
    text = Path("docs/data/d3-4-data-safety.md").read_text(encoding="utf-8")
    for marker in ["Snapshot cadence", "Retention policy", "Restore drill", "Ownership", "Verification", "Incident notes"]:
        assert marker in text, marker
    print("D3.5 DATA READINESS CHECK PASSED")


if __name__ == "__main__":
    main()
