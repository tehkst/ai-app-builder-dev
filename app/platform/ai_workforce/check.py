from __future__ import annotations

from app.platform.ai_workforce.service import build_workforce_summary


def main() -> None:
    summary = build_workforce_summary()
    assert summary["company"] == "AI Software Factory"
    assert summary["product"] == "AI Workforce"
    assert summary["total_employees"] >= 5
    assert summary["active_employees"] == summary["total_employees"]
    departments = set(summary["departments"])
    assert "Executive Office" in departments
    assert "Engineering Command" in departments
    assert "Launch Center" in departments
    assert "Finance" in departments
    print("WORKFORCE CHECK PASSED")


if __name__ == "__main__":
    main()
