"""Check for the Audit: the auditor's briefing (Health Check + impact map), the platform's checks on its
work (evidence files must exist, every fix gets "what breaks if we change this?", sizes get prices,
secrets are scrubbed), the Markdown/PDF report, and the founder-only API with the consent gate,
pinned AI provider, background run and interrupted runs. A scripted Code Auditor; no network."""
from __future__ import annotations

import os
import tempfile
import threading
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


STRIPE = "sk_live_" + "Q" * 24
PEM = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEAsecretbody1234567890abcdef\nmoresecretlines\n-----END RSA PRIVATE KEY-----"


class RecordingPod(Pod):
    """Also records everything sent to the model (tool results included), to prove no secret leaks."""

    def __init__(self, scripts) -> None:
        super().__init__(scripts)
        self.seen: List[str] = []

    def __call__(self, messages, tools):
        self.seen += [str(m.get("content", "")) for m in messages]
        return super().__call__(messages, tools)


def check_redaction(base: Path) -> None:
    from app.platform.clients.redaction import is_secret_file, redact, redact_all, redacted_copy

    for name in (".env", ".env.production", "prod.env", "id_rsa", "server.pem", "site.key", "credentials.json",
                 "service-account-prod.json", ".npmrc", "auth.json", "keystore.jks"):
        assert is_secret_file(name), name
    for name in (".env.example", ".env.sample", "config.php", "README.md", "package.json", "example.key"):
        assert not is_secret_file(name), name
    text = f"key={STRIPE}\n{PEM}\nafter"
    cleaned = redact(text)
    assert STRIPE not in cleaned and "secretbody" not in cleaned and "moresecretlines" not in cleaned and "END RSA" not in cleaned
    assert cleaned.endswith("after"), "text after the key block survives"
    assert redact_all({"a": [PEM, {"b": STRIPE}]}) == {"a": ["[secret removed]", {"b": "[secret removed]"}]}

    source = base / "leaky"
    (source / "config").mkdir(parents=True)
    (source / ".env").write_text(f"STRIPE_KEY={STRIPE}\n")
    (source / ".env.example").write_text("STRIPE_KEY=your-key-here\n")
    (source / "config" / "app.php").write_text(f"<?php\n$stripe = '{STRIPE}';\n$key = <<<KEY\n{PEM}\nKEY;\n")
    (source / "logo.png").write_bytes(b"\x89PNG\0\0binary")
    copy = base / "leaky-copy"
    assert redacted_copy(str(source), str(copy)) == 1
    assert "withheld" in (copy / ".env").read_text() and "your-key-here" in (copy / ".env.example").read_text()
    php = (copy / "config" / "app.php").read_text()
    assert STRIPE not in php and "secretbody" not in php and "$stripe = '[secret removed]'" in php
    assert not (copy / "logo.png").exists()

    pod = RecordingPod({"Code Auditor": [turn("", [call("e", "read_file", path=".env")]),
                                         turn("", [call("c", "read_file", path="config/app.php")]),
                                         turn("", [call("l", "list_files")]), *finish("a", VALID)]})
    before = set(Path(tempfile.gettempdir()).glob("asf-audit-*"))  # e.g. a real Audit running on this machine
    with mock.patch.object(audit, "chat_factory", lambda p, m: pod):
        audit.run_audit(str(source), "leaky", ("openai", "m"), online_lookups=False)
    sent = "\n".join(pod.seen)
    assert "withheld" in sent and "[secret removed]" in sent, "the auditor did read the files"
    assert STRIPE not in sent and "secretbody" not in sent and "moresecretlines" not in sent, "no secret reached the AI"
    assert not set(Path(tempfile.gettempdir()).glob("asf-audit-*")) - before, "the redacted copy is deleted afterwards"

    # Client jobs: secret files never go into the AI team's copy either.
    os.environ["ASF_CLIENT_WORKSPACES"] = str(base / "work-ws")
    job_copy = work.prepare_copy(str(source), "CL-leaky")
    assert not (Path(job_copy["workspace"]) / ".env").exists() and (Path(job_copy["workspace"]) / ".env.example").exists()


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

    release = threading.Event()  # keep the first Audit running until the duplicate start is refused

    def factory(provider_name, model):
        pinned.append((provider_name, model))

        def held(messages, tools):
            release.wait(60)
            return pod(messages, tools)
        return held

    with mock.patch.object(audit, "chat_factory", factory):
        started = post("run-audit", **start)
        assert started["status"] == "started", started
        again = post("run-audit", **start)
        release.set()
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

    from dataclasses import replace

    paid = {"input_tokens": 5000, "output_tokens": 200}
    failing = Pod({"Code Auditor": [replace(turn("I looked around but have nothing to report."), provider="openai",
                                            model="gpt-5.5", usage=paid)] * 2})
    with mock.patch.object(audit, "chat_factory", lambda p, m: failing):
        second = post("run-audit", **start)
        service._RUNNING[second["audit_id"]].join(timeout=120)
    failed = post("detail", client_id=client_id)["client"]["codebases"][0]["audit"]
    assert failed["status"] == "failed" and "without a review" in failed["error"], failed
    assert failed["cost"]["tokens"] == 10_400 and failed["cost"]["calls"] == 2, "a failed Audit keeps its AI cost"

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
        check_redaction(base)
        check_api(root, base)
    print("CLIENT AUDIT CHECK PASSED")


if __name__ == "__main__":
    main()
