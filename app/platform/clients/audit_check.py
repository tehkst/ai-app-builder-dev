"""Check for the Audit: the auditor's briefing (Health Check + impact map), the platform's checks on its
work (evidence files must exist, every fix gets "what breaks if we change this?", sizes get prices,
secrets are scrubbed), the Markdown/PDF report, and the founder-only API with the consent gate,
pinned AI provider, background run and interrupted runs. A scripted Code Auditor; no network."""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Tuple
from unittest import mock

from fastapi.testclient import TestClient

from app.platform.auth.service import _sign_claims
from app.platform.clients import audit, service, work
from app.platform.clients.audit_report import render_markdown, render_pdf
from app.platform.codebase_health.service import run_health_check
from app.platform.impact_map.check import write_project
from app.platform.nautilus.loop_check import call, turn
from app.platform.orca.orca_check import Pod, finish

RAW = {
    "summary": "The shop works but its pricing code is fragile and one package has known holes.",
    "map": [{"part": "Theme", "purpose": "Pages and checkout", "files": ["functions.php", "page-checkout.php"],
             "connects_to": ["Pricing"]}],
    "findings": [
        {"title": "Discount maths duplicated", "severity": "medium", "impact": "Prices can disagree between pages.",
         "fix": "Use Pricing::total everywhere.", "size": "S", "change_target": "Bakery\\Pricing",
         "evidence": [{"file": "inc/pricing.php", "line": 5, "note": "total()"}]},
        {"title": "Old axios with known vulnerabilities", "severity": "high", "impact": "Attackers could abuse requests.",
         "fix": "Upgrade axios to 1.7.", "size": "M", "change_target": "axios",
         "evidence": [{"file": "/src/lib/api.ts", "line": 1}]},
        {"title": "SQL injection in admin", "severity": "critical", "impact": "Anyone could read all orders.",
         "fix": "Use prepared statements.", "size": "XL",
         "evidence": [{"file": "admin/orders.php", "line": 40}]},  # no such file: not verified
        {"title": "Hard-coded API key", "severity": "high", "impact": "Key sk_live_abcdefghijklmnop1234 is exposed.",
         "fix": "Move it to configuration and rotate it.", "size": "S", "inference": True,
         "evidence": [{"file": "../../etc/passwd"}]},
    ],
    "first_steps": ["Rotate the exposed key", "Fix the admin query", "Upgrade axios"],
    "appendix": "Uses WordPress hooks heavily.",
}


# What a real auditor can submit (the schema rejects sizes other than S/M/L; finish() also copes).
VALID = {**RAW, "findings": [{**f, "size": f["size"] if f["size"] in ("S", "M", "L") else "L"} for f in RAW["findings"]]}


def check_finish(root: Path) -> None:
    health = run_health_check(str(root), online_lookups=False)
    brief = audit.assignment("bakery", health)
    assert "inc/pricing.php: used directly by" in brief and "Health Check (automated, grade" in brief
    assert "Never repeat a secret's value" in brief
    result = audit.finish(RAW, str(root), health)
    titles = [f["title"] for f in result["findings"]]
    assert titles[0] == "SQL injection in admin" and titles[1] == "Old axios with known vulnerabilities", titles
    by = {f["title"]: f for f in result["findings"]}
    assert by["Discount maths duplicated"]["verified"] and by["Discount maths duplicated"]["price"] == audit.PRICE_BY_SIZE["S"]
    pricing = by["Discount maths duplicated"]["change_impact"]
    assert pricing["found"] and pricing["kind"] == "class" and "page-checkout.php" in pricing["entry_points"], pricing
    axios = by["Old axios with known vulnerabilities"]
    assert axios["verified"] and axios["evidence"][0]["file"] == "src/lib/api.ts" and axios["change_impact"]["kind"] == "package"
    sql = by["SQL injection in admin"]
    assert not sql["verified"] and not sql["evidence"][0]["exists"] and sql["size"] == "M", "bad size falls back to M"
    key = by["Hard-coded API key"]
    assert not key["verified"] and "sk_live" not in key["impact"] and "[secret removed]" in key["impact"]
    assert not key["evidence"][0]["exists"] and key["evidence"][0]["file"] == "(outside this codebase)", \
        "paths outside the codebase never count as evidence, and never reach the client's report"
    assert result["unverified"] == 2 and result["first_steps"][0] == "Rotate the exposed key"
    assert result["impact"]["hotspots"] and result["health"]["overall"]["grade"] in "ABCDF"
    markdown = render_markdown(result, "bakery")
    for text in ("# Codebase Audit: bakery", "## Do these first", "| 1 | SQL injection in admin (not verified) | Critical |",
                 "**What the fix would touch:** Moderate", "## How the app is put together", "with AI assistance"):
        assert text in markdown, text
    with tempfile.TemporaryDirectory() as out:
        assert Path(render_pdf(result, "bakery", str(Path(out) / "a.pdf"))).read_bytes().startswith(b"%PDF")


def check_api(root: Path, base: Path) -> None:
    os.environ["ASF_CLIENT_WORKSPACES"] = str(base / "workspaces")
    service.HEALTH_CHECK_ONLINE = False
    expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).replace(microsecond=0).isoformat()
    token = _sign_claims({"sub": "founder@example.com", "role": "founder", "exp": expires})
    from app.platform.server import app

    http = TestClient(app)

    def post(path: str, **body):
        return http.post(f"/mission-control/clients/{path}", json={"token": token, **body}).json()

    client_id = post("create", name="Bakery")["client"]["client_id"]
    codebase_id = post("add-codebase", client_id=client_id, source=str(root))["codebase"]["codebase_id"]
    provider = post("detail", client_id=client_id)["ai_provider"]
    start = dict(codebase_id=codebase_id, client_consent=True, ai_provider=provider)
    early = post("run-audit", **start)
    assert early["status"] == "invalid-request" and "Health Check" in early["error"], "the Audit builds on the Health Check"
    post("run-check", codebase_id=codebase_id)
    service._RUNNING[codebase_id].join(timeout=120)
    assert http.post("/mission-control/clients/run-audit", json=start).json()["status"] == "unauthorized"
    for missing in ({"client_consent": False}, {"ai_provider": "elsewhere"}):
        refused = post("run-audit", **{**start, **missing})
        assert refused["status"] == "invalid-request" and "agreed" in refused["error"], refused

    pinned: List[Tuple[str, str]] = []
    pod = Pod({"Code Auditor": [turn("", [call("l", "list_files")]), turn("", [call("r", "read_file", path="inc/pricing.php")]),
                                *finish("a", VALID)]})

    def factory(provider_name, model):
        pinned.append((provider_name, model))
        return pod

    with mock.patch.object(audit, "chat_factory", factory):
        started = post("run-audit", **start)
        assert started["status"] == "started", started
        again = post("run-audit", **start)
        service._RUNNING[started["audit_id"]].join(timeout=120)
    assert again["status"] == "invalid-request" and "already running" in again["error"], again
    assert pinned == [work.current_ai()], f"the audit uses the agreed provider: {pinned}"
    assert "Health Check (automated" in pod.briefings["Code Auditor"][0]
    shown = post("detail", client_id=client_id)["client"]["codebases"][0]["audit"]
    assert shown["status"] == "ready" and shown["ai_provider"] == provider, shown
    assert shown["counts"] == {"critical": 1, "high": 2, "medium": 1, "low": 0} and shown["unverified"] == 2
    assert shown["findings"][0]["title"] == "SQL injection in admin" and shown["findings"][0]["verified"] is False
    discount = next(f for f in shown["findings"] if f["title"] == "Discount maths duplicated")
    assert discount["level"] == "moderate" and discount["affected"] >= 4, discount
    assert [f["severity"] for f in shown["findings"]] == ["critical", "high", "high", "medium"]
    pdf = http.post("/mission-control/clients/audit-report", json={"token": token, "audit_id": started["audit_id"]})
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert http.post("/mission-control/clients/audit-report", json={"audit_id": started["audit_id"]}).status_code == 404

    failing = Pod({"Code Auditor": [turn("I looked around but have nothing to report.")]})
    with mock.patch.object(audit, "chat_factory", lambda p, m: failing):
        second = post("run-audit", **start)
        service._RUNNING[second["audit_id"]].join(timeout=120)
    failed = post("detail", client_id=client_id)["client"]["codebases"][0]["audit"]
    assert failed["status"] == "failed" and "without a review" in failed["error"], failed

    from app.platform.persistence.database import PlatformSessionLocal
    from app.platform.persistence.models import PlatformClientAudit

    with PlatformSessionLocal() as db:  # a run whose worker died with the server
        db.query(PlatformClientAudit).filter_by(audit_id=second["audit_id"]).update({"status": "running", "error": None})
        db.commit()
    stale = post("detail", client_id=client_id)["client"]["codebases"][0]["audit"]
    assert stale["status"] == "failed" and "interrupted" in stale["error"], stale


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp).resolve()
        root = base / "bakery"
        write_project(root)
        check_finish(root)
        check_api(root, base)
    print("CLIENT AUDIT CHECK PASSED")


if __name__ == "__main__":
    main()
