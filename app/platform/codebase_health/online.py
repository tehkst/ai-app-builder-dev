"""Online lookups for the Health Check: end-of-life dates (endoflife.date) and known vulnerabilities
(OSV.dev). Approved by the founder on 2026-10-17.

Only product names, package names and version numbers are sent; never code or file contents. All
network access goes through one `fetch(url, payload)` function so checks can pass a fake one. When
a service can't be reached the result says "not checked" instead of guessing.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

Fetch = Callable[[str, Optional[dict]], Any]
EOL_API = "https://endoflife.date/api/{product}.json"
OSV_BATCH = "https://api.osv.dev/v1/querybatch"
OSV_VULN = "https://api.osv.dev/v1/vulns/{id}"
SOON_DAYS = 180
DETAIL_LIMIT = 25
SEVERITY = {"CRITICAL": "critical", "HIGH": "high", "MODERATE": "moderate", "MEDIUM": "moderate", "LOW": "low"}


class OnlineError(RuntimeError):
    pass


def default_fetch(url: str, payload: Optional[dict] = None) -> Any:
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json",
                                                             "User-Agent": "ai-software-factory-health-check"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read())
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        raise OnlineError(str(exc)) from exc


def eol_status(versions: List[Dict[str, str]], fetch: Fetch, today: Optional[date] = None) -> Dict[str, Any]:
    today = today or date.today()
    results, cache = [], {}
    for item in versions:
        product = item["product"]
        try:
            if product not in cache:
                cache[product] = fetch(EOL_API.format(product=product), None)
        except OnlineError:
            results.append({**item, "status": "not_checked"})
            continue
        cycles = cache[product] or []
        cycle = next((c for c in cycles if str(c.get("cycle")) == item["cycle"]), None)
        cycle = cycle or next((c for c in cycles if str(c.get("cycle")).split(".")[0] == item["cycle"].split(".")[0]), None)
        if not cycle:
            results.append({**item, "status": "unknown"})
            continue
        eol, latest = cycle.get("eol"), cycle.get("latest")
        if eol is True:
            status, eol_date = "end_of_life", None
        elif eol in (False, None):
            status, eol_date = "supported", None
        else:
            eol_date = datetime.strptime(str(eol), "%Y-%m-%d").date()
            status = "end_of_life" if eol_date <= today else "ending_soon" if eol_date <= today + timedelta(days=SOON_DAYS) else "supported"
        results.append({**item, "status": status, "eol": str(eol_date) if eol_date else None, "latest": latest,
                        "newest_cycle": str(cycles[0].get("cycle")) if cycles else None})
    return {"checked": True, "items": results}


def osv_vulnerabilities(packages: List[Dict[str, str]], fetch: Fetch) -> Dict[str, Any]:
    if not packages:
        return {"checked": True, "affected": [], "packages_checked": 0}
    try:
        affected = []
        for start in range(0, len(packages), 500):
            chunk = packages[start:start + 500]
            reply = fetch(OSV_BATCH, {"queries": [{"package": {"name": p["name"], "ecosystem": p["ecosystem"]},
                                                   "version": p["version"]} for p in chunk]})
            for pkg, result in zip(chunk, reply.get("results", [])):
                ids = [v["id"] for v in result.get("vulns") or []]
                if ids:
                    affected.append({**pkg, "ids": ids})
    except OnlineError:
        return {"checked": False, "affected": [], "packages_checked": 0}
    details: Dict[str, Dict[str, str]] = {}
    for vuln_id in [i for a in affected for i in a["ids"]][:DETAIL_LIMIT]:
        if vuln_id in details:
            continue
        try:
            record = fetch(OSV_VULN.format(id=vuln_id), None)
        except OnlineError:
            continue
        details[vuln_id] = {"severity": SEVERITY.get(str((record.get("database_specific") or {}).get("severity", "")).upper(), "unknown"),
                            "summary": str(record.get("summary") or "")[:160]}
    for item in affected:
        item["advisories"] = [{"id": i, **details.get(i, {"severity": "unknown", "summary": ""})} for i in item["ids"]]
        ranks = [a["severity"] for a in item["advisories"]]
        item["worst"] = next((s for s in ("critical", "high", "moderate", "low") if s in ranks), "unknown")
    return {"checked": True, "affected": affected, "packages_checked": len(packages)}
