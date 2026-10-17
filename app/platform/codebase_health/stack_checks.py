"""Health Check v2 scanners: supported versions, known vulnerabilities, risky stack configuration.

Findings are (severity, title, detail) in plain English for a business owner, like scanners.py.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.platform.codebase_health import online
from app.platform.codebase_health.inventory import Inventory
from app.platform.codebase_health.versions import detect_versions, locked_packages, unreadable_lockfiles

Finding = Tuple[str, str, str]


def scan_runtimes(inv: Inventory, fetch: Optional[online.Fetch]) -> Tuple[Dict[str, Any], List[Finding]]:
    versions = detect_versions(inv)
    if fetch is None:
        return {"checked": False, "items": [{**v, "status": "not_checked"} for v in versions]}, []
    data = online.eol_status(versions, fetch)
    findings: List[Finding] = []
    for item in data["items"]:
        name = f"{item['label']} {item['cycle']}"
        upgrade = f" The current release line is {item['label']} {item['newest_cycle']}." if item.get("newest_cycle") else ""
        if item["status"] == "end_of_life":
            since = f" since {item['eol']}" if item.get("eol") else ""
            findings.append(("high", f"{name} is no longer supported{since}",
                             f"It gets no security fixes any more, so newly found holes stay open.{upgrade}"))
        elif item["status"] == "ending_soon":
            findings.append(("medium", f"{name} support ends on {item['eol']}",
                             f"Plan the upgrade now, before security fixes stop.{upgrade}"))
    return data, findings


def scan_vulnerabilities(inv: Inventory, fetch: Optional[online.Fetch]) -> Tuple[Dict[str, Any], List[Finding]]:
    packages = locked_packages(inv)
    unreadable = unreadable_lockfiles(inv)
    if fetch is None:
        return {"checked": False, "packages_found": len(packages), "unreadable_lockfiles": unreadable}, []
    data = online.osv_vulnerabilities(packages, fetch)
    data["unreadable_lockfiles"] = unreadable
    if not data["checked"]:
        return data, []
    affected = data["affected"]
    serious = [a for a in affected if a["worst"] in {"critical", "high"}]
    unrated = [a for a in affected if a["worst"] == "unknown"]
    findings: List[Finding] = []
    if unreadable:
        findings.append(("medium", "Some lockfiles could not be checked",
                         f"{', '.join(unreadable)} could not be read, so vulnerabilities in those packages are unknown."))
    if not packages and not unreadable:
        findings.append(("low", "No exact dependency versions to check",
                         "Without a lockfile the installed versions are unknown, so known vulnerabilities can't be checked."))
    elif serious:
        findings.append(("high", f"{len(serious)} dependencies with serious known vulnerabilities",
                         f"{len(affected)} of {len(packages)} packages have published security advisories; "
                         f"{len(serious)} are rated critical or high. Most are fixed by upgrading those packages."))
    elif unrated:
        findings.append(("high", f"{len(affected)} dependencies with known vulnerabilities, {len(unrated)} not yet rated",
                         "Some advisories have no severity rating yet, so they're treated as serious until reviewed."))
    elif affected:
        findings.append(("medium", f"{len(affected)} dependencies with known vulnerabilities",
                         "None rated critical or high, but they should be upgraded in the next maintenance round."))
    data["affected"] = sorted(affected, key=lambda a: ["critical", "high", "moderate", "low", "unknown"].index(a["worst"]))[:30]
    return data, findings


DJANGO_DEBUG = re.compile(r"(?m)^\s*DEBUG\s*=\s*True\b")
DJANGO_HOSTS = re.compile(r"(?m)^\s*ALLOWED_HOSTS\s*=\s*\[\s*['\"]\*['\"]\s*\]")
WP_DEBUG = re.compile(r"define\(\s*['\"]WP_DEBUG['\"]\s*,\s*true\s*\)", re.IGNORECASE)
LARAVEL_DEBUG = re.compile(r"(?m)^\s*APP_DEBUG\s*=\s*true\b", re.IGNORECASE)


def scan_configuration(inv: Inventory) -> Tuple[Dict[str, Any], List[Finding]]:
    issues: List[Dict[str, str]] = []
    for rel in inv.all_paths:
        name = Path(rel).name
        if name == "wp-config.php" and WP_DEBUG.search(inv.read(rel) or ""):
            issues.append({"file": rel, "issue": "WordPress debug mode is on"})
        elif name == ".env" and LARAVEL_DEBUG.search(inv.read(rel) or ""):
            issues.append({"file": rel, "issue": "Laravel debug mode is on (APP_DEBUG=true)"})
        elif name.endswith(".py") and ("settings" in rel.lower()):
            text = inv.read(rel) or ""
            if DJANGO_DEBUG.search(text):
                issues.append({"file": rel, "issue": "Django DEBUG = True"})
            if DJANGO_HOSTS.search(text):
                issues.append({"file": rel, "issue": "Django accepts any host name (ALLOWED_HOSTS = ['*'])"})
    findings: List[Finding] = []
    debug = [i for i in issues if "debug" in i["issue"].lower()]
    if debug:
        findings.append(("medium", "Debug mode switched on in the code",
                         "If this reaches the live site, error pages show internal details (paths, settings, sometimes "
                         "passwords) to anyone. Debug must be off in production."))
    if any("ALLOWED_HOSTS" in i["issue"] for i in issues):
        findings.append(("low", "Site accepts any host name", "Makes some attacks easier; list the real domain names instead."))
    return {"issues": issues}, findings
