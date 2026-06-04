import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional


ROOT = Path(__file__).resolve().parents[3]
GENERATED_APP = ROOT / "generated_apps" / "crm-saas-multifile-001"
REPAIR_REPORT_DIR = GENERATED_APP / "repair_reports"


def load_report(report_path: Path) -> Optional[Dict]:
    try:
        return json.loads(report_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def summarize_report(report_path: Path) -> Dict:
    report = load_report(report_path)

    if report is None:
        return {
            "path": str(report_path),
            "filename": report_path.name,
            "readable": False,
            "checked_at": None,
            "repair_needed": None,
            "status": "unreadable report",
        }

    release_gate = report.get("release_gate", {})

    return {
        "path": str(report_path),
        "filename": report_path.name,
        "readable": True,
        "checked_at": report.get("checked_at"),
        "repair_needed": report.get("repair_needed"),
        "repair_attempted": report.get("repair_attempted"),
        "auto_edit_enabled": report.get("auto_edit_enabled"),
        "status": report.get("status"),
        "release_gate_passed": release_gate.get("passed"),
        "failed_check_name": (
            report.get("failed_check", {}) or {}
        ).get("name"),
    }


def list_report_files(limit: int) -> List[Path]:
    if not REPAIR_REPORT_DIR.exists():
        return []

    reports = sorted(
        REPAIR_REPORT_DIR.glob("repair_report_*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    return reports[:limit]


def build_index(limit: int) -> Dict:
    report_files = list_report_files(limit)
    reports = [summarize_report(path) for path in report_files]

    return {
        "passed": True,
        "report_directory": str(REPAIR_REPORT_DIR),
        "report_count": len(reports),
        "limit": limit,
        "reports": reports,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List recent self-healing repair reports."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of recent reports to list.",
    )

    args = parser.parse_args()

    if args.limit < 1:
        raise SystemExit("--limit must be at least 1")

    index = build_index(args.limit)

    print(json.dumps(index, indent=2))

    if index["report_count"] == 0:
        print("NO REPAIR REPORTS FOUND")
        return

    print("REPAIR REPORT INDEX READY")


if __name__ == "__main__":
    main()
