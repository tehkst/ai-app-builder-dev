from __future__ import annotations

import importlib
import json
import warnings
from dataclasses import asdict, dataclass
from typing import Any, Dict, List


KNOWN_NON_BLOCKING_PATTERNS = [
    "urllib3 v2 only supports OpenSSL 1.1.1+",
    "The default value of `allowed_objects` will change in a future version",
    "on_event is deprecated, use lifespan event handlers instead",
]


CHECK_IMPORTS = [
    "app.main",
    "app.platform.agents.app_build_dashboard_check",
    "app.platform.agents.app_build_request_run_check",
    "app.platform.services.workflow_run_persistence_service",
]


@dataclass
class CapturedWarning:
    category: str
    message: str
    filename: str
    line_number: int
    classification: str


def classify_warning(message: str) -> str:
    for pattern in KNOWN_NON_BLOCKING_PATTERNS:
        if pattern in message:
            return "known_non_blocking"

    return "unknown_review_required"


def run_dependency_warning_check() -> Dict[str, Any]:
    captured: List[CapturedWarning] = []

    with warnings.catch_warnings(record=True) as warning_records:
        warnings.simplefilter("always")

        for module_name in CHECK_IMPORTS:
            importlib.import_module(module_name)

        for warning_record in warning_records:
            message = str(warning_record.message)
            captured.append(
                CapturedWarning(
                    category=warning_record.category.__name__,
                    message=message,
                    filename=warning_record.filename,
                    line_number=warning_record.lineno,
                    classification=classify_warning(message),
                )
            )

    unknown_warnings = [
        warning for warning in captured
        if warning.classification == "unknown_review_required"
    ]

    return {
        "success": len(unknown_warnings) == 0,
        "checked_imports": CHECK_IMPORTS,
        "known_non_blocking_patterns": KNOWN_NON_BLOCKING_PATTERNS,
        "warning_count": len(captured),
        "unknown_warning_count": len(unknown_warnings),
        "warnings": [asdict(warning) for warning in captured],
    }


def main() -> None:
    result = run_dependency_warning_check()
    print(json.dumps(result, indent=2, sort_keys=True))

    if not result["success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
