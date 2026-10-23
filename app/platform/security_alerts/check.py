"""Check for the security alert sweep: the alerts file is valid, version matching gives the four honest
answers (affected / check the server / patched / not applicable), the Health Check turns matches into
risks, and the founder-only sweep checks every client's code (offline) with missing code reported."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.platform.auth.service import _sign_claims
from app.platform.codebase_health.inventory import build_inventory
from app.platform.codebase_health.versions import PRODUCTS
from app.platform.security_alerts import load_alerts, match_alert, match_inventory

ALERT = "CSA-AL-2026-151"


def project(base: Path, name: str, files: dict) -> Path:
    root = base / name
    for rel, content in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(content)
    return root


def check_file() -> None:
    alerts = load_alerts()
    ids = [a["id"] for a in alerts]
    assert ALERT in ids and len(ids) == len(set(ids)), ids
    for a in alerts:
        assert a["product"] in PRODUCTS, a["product"]
        assert str(a.get("source", "")).startswith("https://") and a.get("severity") in ("critical", "high", "medium", "low")
        for branch, fixed in (a.get("fixed") or {}).items():
            assert str(fixed).startswith(str(branch) + "."), (branch, fixed)
        assert (a.get("job") or {}).get("kind") in ("upgrade", "fix"), a.get("job")
    php = next(a for a in alerts if a["id"] == ALERT)
    assert php["fixed"] == {"8.5": "8.5.12", "8.4": "8.4.27", "8.3": "8.3.36", "8.2": "8.2.35"}


def check_matching() -> None:
    alert = next(a for a in load_alerts() if a["id"] == ALERT)

    def status(version: str, source: str, constraint: str = "") -> str:
        cycle = ".".join(version.split(".")[:2])
        item = {"product": "php", "version": version, "cycle": cycle, "source": source, "constraint": constraint or version}
        return match_alert(alert, [item], True)["status"]

    cases = {("8.3.30", "Dockerfile"): "affected", ("8.3.36", "Dockerfile"): "patched", ("8.3.40", "docker/Dockerfile.prod"): "patched",
             ("8.2.34", ".php-version"): "affected", ("8.3", "Dockerfile"): "check_server", ("8.3.30", "composer.json"): "check_server",
             ("7.4.33", "Dockerfile"): "affected", ("8.6.0", "Dockerfile"): "patched", ("8.1", "Dockerfile"): "affected"}
    for (version, source), expected in cases.items():
        assert status(version, source) == expected, (version, source, status(version, source))
    # A minimum (^8.1, >=8.1) allows newer, supported PHP: the server decides. A pin keeps the old branch.
    for constraint, expected in (("^8.1", "check_server"), (">=8.1", "check_server"), ("8.1.*", "affected"),
                                 ("~8.1.0", "affected"), ("8.1.27", "affected")):
        assert status("8.1", "composer.json", constraint) == expected, (constraint, status("8.1", "composer.json", constraint))
    minimum = match_alert(alert, [{"product": "php", "version": "8.1", "cycle": "8.1", "source": "composer.json", "constraint": "^8.1"}], True)
    assert "8.3.36+" in minimum["reason"] and "or newer" in minimum["reason"], minimum["reason"]
    unknown = match_alert(alert, [], True)
    assert unknown["status"] == "check_server" and "8.3.36" in unknown["fixed_versions"]
    assert match_alert(alert, [], False)["status"] == "not_applicable"
    affected = match_alert(alert, [{"product": "php", "version": "8.3.30", "cycle": "8.3", "source": "Dockerfile"}], True)
    assert affected["fixed_version"] == "8.3.36" and "8.3.30" in affected["reason"]


def check_health_check(base: Path) -> None:
    from app.platform.codebase_health.service import run_health_check

    docker = project(base, "docker-php", {"Dockerfile": "FROM php:8.3.30-apache\n", "index.php": "<?php echo 1;\n"})
    composer = project(base, "composer-php", {"composer.json": json.dumps({"require": {"php": "^8.3"}}), "index.php": "<?php\n"})
    node = project(base, "node-only", {"package.json": json.dumps({"name": "n"}), "index.js": "console.log(1)\n"})
    assert [a["status"] for a in match_inventory(build_inventory(docker))] == ["affected"]
    assert [a["status"] for a in match_inventory(build_inventory(composer))] == ["check_server"]
    assert match_inventory(build_inventory(node)) == [], "alerts for other products are not listed"
    both = project(base, "both", {"composer.json": json.dumps({"require": {"php": "^8.3"}}),
                                  "Dockerfile": "FROM php:8.3.30-apache\n", "index.php": "<?php\n"})
    assert [a["status"] for a in match_inventory(build_inventory(both))] == ["affected"], "the exact Docker tag wins over ^8.3"
    pinned = project(base, "php-version", {".php-version": "8.2.34\n", "composer.json": json.dumps({"require": {"php": ">=8.1"}}),
                                           "index.php": "<?php\n"})
    found = match_inventory(build_inventory(pinned))
    assert [a["status"] for a in found] == ["affected"] and found[0]["source"] == ".php-version", found

    result = run_health_check(str(docker), online_lookups=False)
    titles = [r["title"] for r in result["all_risks"]]
    assert any(t.startswith(f"Affected by {ALERT}") for t in titles), titles
    assert result["overall"]["grade"] != "A", "an affected alert is a high-severity risk"
    vulns = next(a for a in result["areas"] if a["key"] == "vulnerabilities")
    assert vulns["data"]["alerts"][0]["status"] == "affected"
    medium = run_health_check(str(composer), online_lookups=False)
    assert any(r["title"].startswith(f"Check the server for {ALERT}") and r["severity"] == "medium" for r in medium["all_risks"])


def check_api(base: Path) -> None:
    from app.platform.clients import service
    from app.platform.server import app

    os.environ["ASF_CLIENT_WORKSPACES"] = str(base / "workspaces")
    service.HEALTH_CHECK_ONLINE = False
    expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).replace(microsecond=0).isoformat()
    token = _sign_claims({"sub": "founder@example.com", "role": "founder", "exp": expires})
    http = TestClient(app)

    def post(path: str, **body):
        return http.post(f"/mission-control/clients/{path}", json={"token": token, **body}).json()

    shop = post("create", name="Old PHP Shop")["client"]["client_id"]
    post("add-codebase", client_id=shop, source=str(project(base, "old-shop", {"Dockerfile": "FROM php:8.1-fpm\n", "a.php": "<?php\n"})))
    gone = post("add-codebase", client_id=shop, source=str(project(base, "gone", {"b.php": "<?php\n"})))["codebase"]
    import shutil

    shutil.rmtree(base / "gone")
    assert http.post("/mission-control/clients/security-alerts", json={}).json()["status"] == "unauthorized"
    assert any(a["id"] == ALERT for a in post("security-alerts")["alerts"])
    assert http.post("/mission-control/clients/alert-sweep", json={"alert_id": ALERT}).json()["status"] == "unauthorized"
    assert post("alert-sweep", alert_id="NOPE")["status"] == "invalid-request"
    rows = [r for r in post("alert-sweep", alert_id=ALERT)["results"] if r["client_id"] == shop]
    assert [r["status"] for r in rows] == ["affected", "missing"], rows
    assert rows[0]["client_name"] == "Old PHP Shop" and "no official fix" in rows[0]["reason"]
    assert rows[1]["codebase_id"] == gone["codebase_id"]


def main() -> None:
    check_file()
    check_matching()
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp).resolve()
        check_health_check(base)
        check_api(base)
    print("SECURITY ALERTS CHECK PASSED")


if __name__ == "__main__":
    main()
