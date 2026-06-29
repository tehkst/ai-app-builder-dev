from __future__ import annotations

from pathlib import Path

from app.platform.health import build_health_status, build_readiness_status


def assert_contains(path: str, text: str) -> None:
    content = Path(path).read_text()
    assert text in content, "{} missing {}".format(path, text)


def main() -> None:
    assert Path("app/platform/health/health_status.py").exists()
    assert_contains("app/platform/server.py", "build_health_status")
    assert_contains("app/platform/server.py", "build_readiness_status")
    assert_contains("app/platform/server.py", "@app.get(\"/health\")")
    assert_contains("app/platform/server.py", "@app.get(\"/ready\")")

    health = build_health_status()
    ready = build_readiness_status()

    assert health["status"] == "healthy", health
    assert health["service"], health
    assert health["version"] == "1.0.0", health
    assert isinstance(health["components"], list), health

    assert ready["status"] == "ready", ready
    assert ready["service"], ready
    assert ready["version"] == "1.0.0", ready
    assert len(ready["components"]) >= 3, ready

    print("HEALTH READINESS CHECK PASSED")


if __name__ == "__main__":
    main()
