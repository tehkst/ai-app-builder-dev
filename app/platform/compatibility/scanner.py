import ast
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
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    try:
        tree = ast.parse(source, filename=path.as_posix(), feature_version=(3, 9))
    except SyntaxError as exc:
        return [
            {
                "file_path": path.as_posix(),
                "line_number": exc.lineno,
                "pattern": "python_39_syntax",
                "issue": "File cannot be parsed with the Python 3.9 grammar.",
                "line": (exc.text or "").strip(),
            }
        ]

    postponed_annotations = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(alias.name == "annotations" for alias in node.names)
        for node in tree.body
    )
    if postponed_annotations:
        return issues

    rule = PYTHON_39_FORBIDDEN_PATTERNS[0]
    for node in ast.walk(tree):
        if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.BitOr):
            continue
        line_number = getattr(node, "lineno", None)
        issues.append(
            {
                "file_path": path.as_posix(),
                "line_number": line_number,
                "pattern": rule["pattern"],
                "issue": rule["issue"],
                "line": lines[line_number - 1].strip() if line_number else "",
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
