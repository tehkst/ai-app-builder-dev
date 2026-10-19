"""Check for the Clients area: founder-only API, safe sources, background Health Check, PDF, jobs,
and the exact git command used to fetch client code (captured, not run)."""
from __future__ import annotations

import os
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from app.platform.auth.service import _sign_claims
from app.platform.clients import fetch, service
from app.platform.server import app


def check_api(base: Path) -> None:
    os.environ["ASF_CLIENT_WORKSPACES"] = str(base / "workspaces")
    service.HEALTH_CHECK_ONLINE = False
    expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).replace(microsecond=0).isoformat()
    token = _sign_claims({"sub": "founder@example.com", "role": "founder", "exp": expires})
    client = TestClient(app)

    def post(path: str, **body):
        return client.post(f"/mission-control/clients/{path}", json={"token": token, **body}).json()

    assert client.post("/mission-control/clients/list", json={}).json()["status"] == "unauthorized"
    created = post("create", name="Kopi Corner", contact="owner@kopi.test")
    client_id = created["client"]["client_id"]
    assert post("create", name="  ")["status"] == "invalid-request"
    for bad in ("https://user:pw@github.com/a/b", "git@github.com:a/b.git", "http://example.com/a.git",
                "file:///etc", "ext::sh -c id", str(Path.home()), "relative/path"):
        assert post("add-codebase", client_id=client_id, source=bad)["status"] == "invalid-request", bad

    project = base / "kopi-app"
    project.mkdir()
    (project / "README.md").write_text("# Kopi app\n")
    (project / "app.py").write_text("print('hello')\n")
    codebase = post("add-codebase", client_id=client_id, source=str(project))["codebase"]
    assert codebase["status"] == "ready" and codebase["label"] == "kopi-app"
    assert post("run-check", codebase_id=codebase["codebase_id"])["status"] == "started"
    service._RUNNING[codebase["codebase_id"]].join(timeout=120)
    detail = post("detail", client_id=client_id)["client"]
    checked = detail["codebases"][0]
    assert checked["status"] == "ready" and checked["last_check"]["overall"]["grade"] in "ABCDF", checked
    assert checked["has_report"] and not checked["running"]
    pdf = client.post("/mission-control/clients/report", json={"token": token, "codebase_id": codebase["codebase_id"]})
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert client.post("/mission-control/clients/report", json={"codebase_id": codebase["codebase_id"]}).status_code == 404

    job = post("add-job", client_id=client_id, title="Health Check", kind="health_check", price="$79")["job"]
    assert job["status"] == "lead"
    assert post("update-job", job_id=job["job_id"], status="delivered")["job"]["status"] == "delivered"
    assert post("update-job", job_id=job["job_id"], status="hacked")["status"] == "invalid-request"
    assert post("add-job", client_id=client_id, title="x", kind="rocket")["status"] == "invalid-request"
    assert post("update", client_id=client_id, status="active")["status"] == "updated"
    listed = {c["client_id"]: c for c in post("list")["clients"]}
    assert listed[client_id]["status"] == "active" and len(listed[client_id]["jobs"]) == 1


def check_git_command(base: Path) -> None:
    captured = {}

    def fake_run(args, env=None, **kwargs):
        captured.update(args=args, env=env, askpass=Path(env["GIT_ASKPASS"]).read_text() if env and "GIT_ASKPASS" in env else "")
        Path(args[-1]).mkdir(parents=True)
        return subprocess.CompletedProcess(args, 0, "", "")

    with mock.patch.object(fetch.subprocess, "run", fake_run):
        fetch.clone("https://github.com/acme/shop", base / "clone-a", token="ghp_secret_token_value")
    args, env = captured["args"], captured["env"]
    assert "ghp_secret_token_value" not in " ".join(args), "the token must never be on the command line"
    assert env["ASF_GIT_TOKEN"] == "ghp_secret_token_value" and "ghp_secret" not in captured["askpass"]
    for flag in ("protocol.allow=never", "protocol.https.allow=always", "core.hooksPath=/dev/null", "--no-recurse-submodules"):
        assert flag in args, flag
    assert env["GIT_LFS_SKIP_SMUDGE"] == "1" and env["GIT_TERMINAL_PROMPT"] == "0"
    with mock.patch.object(fetch.subprocess, "run", fake_run):
        fetch.clone("https://gitlab.com/acme/shop", base / "clone-b", token="ghp_secret_token_value")
    assert "ASF_GIT_TOKEN" not in captured["env"], "the GitHub token is only sent to github.com"


def main() -> None:
    with tempfile.TemporaryDirectory() as base:
        check_api(Path(base))
        check_git_command(Path(base))
    print("CLIENTS CHECK PASSED")


if __name__ == "__main__":
    main()
