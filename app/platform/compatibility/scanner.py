import json
from pathlib import Path
from typing import Any, Dict, List

from app.platform.compatibility.policy import (
    FACTORY_RUNTIME_EXCLUDED_PATHS,
    FACTORY_RUNTIME_SCAN_PATHS,
    PYTHON_39_FORBIDDEN_PATTERNS,
)


PYTHON_SUFFIX = ".py"


def is_excluded(path: Path) -> bool:
    normalized = path.as_posix()

    for excluded in FACTORY_RUNTIME_EXCLUDED_PATHS:
        if normalized == excluded or normalized.startswith(excluded.rstrip("/") + "/"):
            return True

    return False


def iter_python_files() -> List[Path]:
    files: List[Path] = []

    for scan_path in FACTORY_RUNTIME_SCAN_PATHS:
        path = Path(scan_path)

        if not path.exists():
            continue

        if path.is_file() and path.suffix == PYTHON_SUFFIX and not is_excluded(path):
            files.append(path)
            continue

        if path.is_dir():
            for candidate in path.rglob("*.py"):
                if not is_excluded(candidate):
                    files.append(candidate)

    return sorted(files)


def scan_file(path: Path) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    lines = path.read_text(encoding="utf-8").splitlines()

    for line_number, line in enumerate(lines, start=1):
        for rule in PYTHON_39_FORBIDDEN_PATTERNS:
            pattern = rule["pattern"]

            if pattern in line:
                issues.append(
                    {
                        "file_path": path.as_posix(),
                        "line_number": line_number,
                        "pattern": pattern,
                        "issue": rule["issue"],
                        "line": line.strip(),
                    }
                )

    return issues


def run_compatibility_scan() -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    files = iter_python_files()

    for file_path in files:
        issues.extend(scan_file(file_path))

    return {
        "passed": len(issues) == 0,
        "files_scanned": len(files),
        "issues": issues,
    }


def main() -> int:
    report = run_compatibility_scan()
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
