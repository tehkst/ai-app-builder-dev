from __future__ import annotations

from app.platform.mission_control.service import build_mission_control_summary


def main() -> None:
    summary = build_mission_control_summary()
    assert summary.company == "AI Software Factory"
    assert summary.product == "Mission Control"
    assert summary.health == "healthy"
    assert len(summary.cards) >= 4
    assert len(summary.departments) >= 6
    assert len(summary.principles) >= 3
    department_names = {department.name for department in summary.departments}
    assert "Executive Office" in department_names
    assert "Engineering Command" in department_names
    assert "AI Workforce" in department_names
    assert "Knowledge Vault" in department_names
    assert "Launch Center" in department_names
    assert "Finance" in department_names
    print("MISSION CONTROL FOUNDATION CHECK PASSED")


if __name__ == "__main__":
    main()
