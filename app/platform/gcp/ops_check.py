from __future__ import annotations

from pathlib import Path

REQUIRED = [
    "infra/terraform/modules/ops/main.tf",
    "infra/terraform/modules/ops/variables.tf",
    "infra/terraform/modules/ops/outputs.tf",
]


def main() -> None:
    missing = [path for path in REQUIRED if not Path(path).exists()]
    assert not missing, f"Missing ops files: {missing}"
    content = Path("infra/terraform/modules/ops/main.tf").read_text(encoding="utf-8")
    assert "google_logging_metric" in content
    assert "google_monitoring_alert_policy" in content
    assert "google_monitoring_dashboard" in content
    print("P1.8 OPS CHECK PASSED")


if __name__ == "__main__":
    main()
