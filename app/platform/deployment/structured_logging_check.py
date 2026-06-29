from __future__ import annotations

import json
from pathlib import Path

from app.platform.logging import build_log_record, new_request_id


def assert_contains(path: str, text: str) -> None:
    content = Path(path).read_text()
    assert text in content, "{} missing {}".format(path, text)


def main() -> None:
    assert Path("app/platform/logging/structured.py").exists()
    assert Path("app/platform/logging/middleware.py").exists()
    assert Path("app/platform/logging/install.py").exists()

    assert_contains("app/platform/server.py", "install_request_logging")
    assert_contains("app/platform/logging/structured.py", "JsonLogFormatter")
    assert_contains("app/platform/logging/structured.py", "request_id")
    assert_contains("app/platform/logging/middleware.py", "x-request-id")
    assert_contains("app/platform/logging/middleware.py", "duration_ms")

    request_id = new_request_id()
    record = build_log_record("INFO", "test message", request_id=request_id, path="/health")
    encoded = json.dumps(record)
    decoded = json.loads(encoded)
    assert decoded["level"] == "info", decoded
    assert decoded["message"] == "test message", decoded
    assert decoded["request_id"] == request_id, decoded
    assert decoded["path"] == "/health", decoded

    print("STRUCTURED LOGGING CHECK PASSED")


if __name__ == "__main__":
    main()
