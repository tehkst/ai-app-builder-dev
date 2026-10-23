"""Match security alerts against client codebases (read-only, offline: nothing is sent anywhere).

The Health Check knows which runtime a codebase targets and where it read that from. That gives four
honest answers per alert:

- affected:      the exact version is known (e.g. Dockerfile `php:8.3.30-apache`) and is below the
                 fixed version, or the branch gets no official fix at all (e.g. PHP 8.1);
- check_server:  the code only declares a branch (e.g. composer `"php": "^8.3"`), so the live server's
                 patch level decides: it must run at least the fixed version;
- patched:       the exact version is at or above the fix;
- not_applicable: the codebase doesn't use the product.

Code tells us what a site *targets*, not what the server *runs*; check_server says so instead of
guessing.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml

from app.platform.codebase_health.inventory import Inventory, build_inventory
from app.platform.codebase_health.versions import detect_versions

REPO_ROOT = Path(__file__).resolve().parents[3]
ALERTS_FILE = REPO_ROOT / "company" / "security-alerts.yaml"
# Where a version is exact (the runtime itself), not a minimum or a constraint.
EXACT_SOURCES = ("dockerfile", ".php-version", ".nvmrc", ".node-version", ".python-version", "runtime.txt")
# Files whose presence means the codebase uses the product even when no version is declared.
PRODUCT_FILES = {"php": (".php",), "nodejs": (".js", ".ts", ".mjs", ".cjs"), "python": (".py",)}


def load_alerts(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    try:
        data = yaml.safe_load((path or ALERTS_FILE).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return []
    return [a for a in data.get("alerts") or [] if a.get("id") and a.get("product")]


def _parts(version: str) -> Tuple[int, ...]:
    return tuple(int(p) for p in re.findall(r"\d+", str(version))[:3])


def _exact(item: Dict[str, str]) -> bool:
    source = str(item.get("source") or "").lower()
    return len(_parts(item["version"])) >= 3 and (Path(source).name.startswith("dockerfile") or source in EXACT_SOURCES)


def _pinned(item: Dict[str, str]) -> bool:
    """A constraint that keeps the site on one branch (e.g. "8.1.*", "~8.1.0", "8.1.10"), not a minimum."""
    if Path(str(item.get("source") or "")).name.lower().startswith("dockerfile"):
        return True  # an image tag (php:8.1-fpm) fixes the branch
    raw = str(item.get("constraint") or "")
    return bool(re.fullmatch(r"\s*(=?\s*\d+\.\d+(\.\d+|\.\*)?|~\s*\d+\.\d+\.\d+)\s*", raw))


def match_alert(alert: Dict[str, Any], versions: List[Dict[str, str]], uses_product: bool) -> Dict[str, Any]:
    """One codebase against one alert: {status, version, source, fixed_version, reason}."""
    product = alert["product"]
    item = next((v for v in versions if v.get("product") == product), None)
    fixed = {str(k): str(v) for k, v in (alert.get("fixed") or {}).items()}
    if item is None:
        if not uses_product:
            return {"status": "not_applicable", "reason": f"No {product} in this codebase."}
        return {"status": "check_server", "reason": f"Uses {product} but doesn't say which version: check the server.",
                "fixed_versions": sorted(fixed.values(), key=_parts)}
    branch = ".".join(str(p) for p in _parts(item["cycle"])[:2]) or item["cycle"]
    base = {"version": item["version"], "source": item.get("source"), "branch": branch}
    oldest = alert.get("unsupported_below")
    if oldest and _parts(branch) < _parts(str(oldest)):
        if _exact(item) or _pinned(item):
            return {**base, "status": "affected", "fixed_version": None,
                    "reason": f"Runs {product} {item['version']} ({item.get('source')}): that branch gets no official fix; "
                              "move to a supported branch (or a vendor's patched build)."}
        supported = ", ".join(f"{v}+" for v in sorted(fixed.values(), key=_parts))
        return {**base, "status": "check_server", "fixed_versions": sorted(fixed.values(), key=_parts),
                "reason": f"The code allows {product} {branch} or newer ({item.get('source')}). Branches before {oldest} get "
                          f"no fix: the server must run a patched supported version ({supported})."}
    if branch not in fixed:
        newest = max(fixed, key=_parts) if fixed else None
        if newest and _parts(branch) > _parts(newest):
            return {**base, "status": "patched", "reason": f"{product} {branch} is newer than every affected branch."}
        return {**base, "status": "check_server", "reason": f"The alert doesn't list {product} {branch}: check the advisory."}
    target = fixed[branch]
    if _exact(item):
        if _parts(item["version"]) < _parts(target):
            return {**base, "status": "affected", "fixed_version": target,
                    "reason": f"Runs {product} {item['version']} ({item.get('source')}); fixed in {target}."}
        return {**base, "status": "patched", "fixed_version": target, "reason": f"{item['version']} includes the fix ({target})."}
    return {**base, "status": "check_server", "fixed_version": target,
            "reason": f"The code targets {product} {branch} ({item.get('source')}); the server must run {target} or newer."}


def match_inventory(inv: Inventory, alerts: Optional[Iterable[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Every alert that concerns this codebase (affected, check_server or patched), for one inventory."""
    versions = detect_versions(inv)
    suffixes = {Path(f.path).suffix.lower() for f in inv.files}
    found = []
    for alert in alerts if alerts is not None else load_alerts():
        uses = bool(suffixes & set(PRODUCT_FILES.get(alert["product"], ())))
        result = match_alert(alert, versions, uses)
        if result["status"] != "not_applicable":
            found.append({"alert_id": alert["id"], "title": alert.get("title"), "severity": alert.get("severity"),
                          "source": alert.get("source"), **result})
    return found


def sweep(codebases: Iterable[Dict[str, Any]], alert_id: str) -> List[Dict[str, Any]]:
    """One alert against many codebases ({codebase_id, client_id, client_name, label, local_path})."""
    alert = next((a for a in load_alerts() if a["id"] == alert_id), None)
    if alert is None:
        raise ValueError("No such alert.")
    order = {"affected": 0, "check_server": 1, "patched": 2, "not_applicable": 3, "missing": 4}
    rows = []
    for cb in codebases:
        path = cb.get("local_path")
        if not path or not Path(path).is_dir():
            rows.append({**_ids(cb), "status": "missing", "reason": "The code isn't on this machine; fetch it again."})
            continue
        inv = build_inventory(Path(path))
        uses = bool({Path(f.path).suffix.lower() for f in inv.files} & set(PRODUCT_FILES.get(alert["product"], ())))
        rows.append({**_ids(cb), **match_alert(alert, detect_versions(inv), uses)})
    return sorted(rows, key=lambda r: (order.get(r["status"], 9), r.get("client_name") or ""))


def _ids(cb: Dict[str, Any]) -> Dict[str, Any]:
    return {k: cb.get(k) for k in ("codebase_id", "client_id", "client_name", "label")}
