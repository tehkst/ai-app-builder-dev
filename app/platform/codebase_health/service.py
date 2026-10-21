"""Codebase Health Check: a quick, automated, read-only scorecard of a client codebase.

The first step of the client service (Health Check -> Audit -> care plan): an Audit starts from these
results and goes deeper. Nothing from the codebase is executed; secrets are reported by location
and kind only. Entry points: `run_health_check(path)` and `python -m app.platform.codebase_health`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.platform.codebase_health import online, scanners, stack_checks
from app.platform.codebase_health.inventory import build_inventory

CONTRACT = "codebase-health-v1"
# area -> (title, weight in the overall score, scanner)
AREAS = (
    ("security", "Security", 25, lambda inv, root, fetch: scanners.scan_secrets(inv)),
    ("vulnerabilities", "Known vulnerabilities", 20, lambda inv, root, fetch: stack_checks.scan_vulnerabilities(inv, fetch)),
    ("tests", "Tests and CI", 20, lambda inv, root, fetch: scanners.scan_tests_and_ci(inv)),
    ("runtimes", "Supported versions", 15, lambda inv, root, fetch: stack_checks.scan_runtimes(inv, fetch)),
    ("dependencies", "Dependencies", 10, lambda inv, root, fetch: scanners.scan_dependencies(inv)),
    ("configuration", "Configuration", 10, lambda inv, root, fetch: stack_checks.scan_configuration(inv)),
    ("maintainability", "Maintainability", 10, lambda inv, root, fetch: scanners.scan_size(inv)),
    ("documentation", "Documentation", 5, lambda inv, root, fetch: scanners.scan_docs(inv)),
    ("activity", "Activity and ownership", 5, lambda inv, root, fetch: scanners.scan_git(root)),
    ("licence", "Licence", 5, lambda inv, root, fetch: scanners.scan_license(inv)),
)
PENALTY = {"high": 50, "medium": 25, "low": 10}
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
NEXT_STEPS = {
    "security": "Rotate the exposed keys and move them to environment variables or a secrets manager (same day).",
    "vulnerabilities": "Upgrade the vulnerable packages, most serious first, testing after each step.",
    "runtimes": "Upgrade the unsupported runtime or framework on a staging copy first, then switch over.",
    "configuration": "Turn debug mode off for the live site and keep settings in environment variables.",

    "tests": "Add a safety net: tests for the most important flows and CI that runs them on every change.",
    "dependencies": "Pin and upgrade dependencies in small, tested steps; set up automatic security alerts.",
    "maintainability": "Split the largest files while fixing or adding features there, not all at once.",
    "documentation": "Write setup and deployment notes so anyone can run the app, not only its author.",
    "activity": "Agree an owner and a regular update rhythm (a care plan) so the app doesn't fall behind again.",
    "licence": "Confirm in writing who owns the code (and add a licence file) before investing in it.",
}


def grade(score: int) -> str:
    return "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D" if score >= 40 else "F"


def _impact(inv, areas: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The impact map preview for the report (step 4d): where changes ripple most, and which files use
    each package with a known vulnerability (what an upgrade would touch)."""
    from app.platform.impact_map import build_map, package_reach, summary

    try:
        imap = build_map(str(inv.root), inventory=inv)
    except Exception as exc:  # the map is extra evidence: never fail the Health Check over it
        return {"error": f"The impact map could not be built: {str(exc)[:200]}"}
    vulnerable = [a["name"] for area in areas if area["key"] == "vulnerabilities"
                  for a in (area["data"].get("affected") or [])]
    return {**summary(imap), "vulnerable_packages": package_reach(imap, vulnerable)}


def run_health_check(path: str, online_lookups: bool = True, fetch: Optional[online.Fetch] = None) -> Dict[str, Any]:
    """online_lookups=False skips endoflife.date and OSV.dev (the report then says "not checked")."""
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Not a folder: {root}")
    inv = build_inventory(root)
    areas: List[Dict[str, Any]] = []
    risks: List[Dict[str, str]] = []
    for key, title, weight, scan in AREAS:
        data, findings = scan(inv, root, (fetch or online.default_fetch) if online_lookups else None)
        score = max(0, 100 - sum(PENALTY[sev] for sev, _, _ in findings))
        areas.append({"key": key, "title": title, "weight": weight, "score": score, "grade": grade(score),
                      "findings": [{"severity": s, "title": t, "detail": d} for s, t, d in findings], "data": data})
        risks += [{"area": title, "area_key": key, "severity": s, "title": t, "detail": d} for s, t, d in findings]
    overall = round(sum(a["score"] * a["weight"] for a in areas) / sum(a["weight"] for a in areas))
    highs = sum(1 for r in risks if r["severity"] == "high")
    overall_grade = grade(overall)
    cap = "C" if highs >= 2 else "B" if highs == 1 else None
    capped = bool(cap) and "ABCDF".index(overall_grade) < "ABCDF".index(cap)
    if capped:
        overall_grade = cap  # serious risks can't hide behind a good average
    risks.sort(key=lambda r: (SEVERITY_ORDER[r["severity"]], -next(a["weight"] for a in areas if a["key"] == r["area_key"])))
    next_steps, seen = [], set()
    for risk in risks:
        if risk["area_key"] not in seen and risk["severity"] in {"high", "medium"}:
            seen.add(risk["area_key"])
            next_steps.append(NEXT_STEPS[risk["area_key"]])
    return {
        "contract": CONTRACT,
        "project": root.name,
        "checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "stack": inv.stack,
        "size": {"files": len(inv.files), "lines": sum(f.lines for f in inv.files)},
        "overall": {"score": overall, "grade": overall_grade,
                    "grade_note": (f"Grade capped at {cap} because of {highs} high-severity risk"
                                   f"{'s' if highs > 1 else ''}." if capped else None)},
        "areas": areas,
        "top_risks": risks[:5],
        "all_risks": risks,
        "next_steps": next_steps[:5],
        "impact": _impact(inv, areas),
        "method": ("Automated, read-only scan: files, manifests and git history were read; no code from the project was run. "
                   + ("Supported versions were checked with endoflife.date and known vulnerabilities with OSV.dev; only "
                      "product and package names with version numbers were sent, never code." if online_lookups else
                      "Offline run: supported versions and known vulnerabilities were not checked.")),
    }
