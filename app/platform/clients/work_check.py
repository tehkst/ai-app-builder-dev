"""Check for step 4a, the AI team on client code: consent gate, disposable copy with history outside
it, every command in the container sandbox (right image, no network, dependencies installed once and
copied back), the diff of the changes, and Home/Clients views. Scripted employees, a fake sandbox
(no Docker needed); a real Docker run is added when Docker and the Node image are available."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock

from fastapi.testclient import TestClient

from app.platform.auth.service import _sign_claims
from app.platform.clients import service
from app.platform.container_sandbox import service as sandbox
from app.platform.orca import MissionStore, Orca, api_service, gates, runner, sandbox_commands
from app.platform.orca.execution_policy import check_command_allowed
from app.platform.orca.orca_check import PASS, Pod, finish, write
from app.platform.server import app

PLAN = {"summary": "Fix the greeting.", "tasks": [
    {"title": "Return hello", "description": "greet() must return 'hello'.", "specialty": "backend",
     "files": ["greet.js"], "acceptance_checks": ["npm test"]}]}


class FakeSandbox:
    """Records every sandbox run. `npm test` passes once greet.js says hello (read from the copy the
    sandbox would mount); installs create the dependency folder in a kept scratch copy."""

    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []
        self.kept: List[str] = []

    def __call__(self, source_dir, command, image, **options) -> sandbox.SandboxResult:
        self.calls.append({"source": source_dir, "command": list(command), "image": image, **options})
        base = dict(command=list(command), image=image, timed_out=False, duration_seconds=0.1,
                    network=options.get("network_reason") is not None)
        if options.get("keep_workdir"):
            scratch = Path(tempfile.mkdtemp(prefix="fake-sbx-"))
            self.kept.append(str(scratch))
            (scratch / "work" / "node_modules" / "left-pad").mkdir(parents=True)
            (scratch / "work" / "node_modules" / "left-pad" / "index.js").write_text("module.exports=1\n")
            return sandbox.SandboxResult(exit_code=0, stdout="added 1 package", stderr="", workdir=str(scratch / "work"), **base)
        if command == ["npm", "test"]:
            ok = "hello" in (Path(source_dir) / "greet.js").read_text()
            return sandbox.SandboxResult(exit_code=0 if ok else 1, stdout="1 passing" if ok else "1 failing", stderr="", **base)
        return sandbox.SandboxResult(exit_code=0, stdout="", stderr="", **base)


def check_policy_and_images(base: Path) -> None:
    for allowed in ("vendor/bin/phpunit", "./vendor/bin/phpunit --filter Cart", "composer test", "php -l src/Cart.php", "npm test"):
        assert check_command_allowed(allowed, str(base))[0], allowed
    for refused in ("php -r 'echo 1;'", "composer install", "php artisan migrate", "sh -c 'npm test'", "php -l /etc/passwd"):
        assert not check_command_allowed(refused, str(base))[0], refused
    php = base / "php-app"
    php.mkdir()
    (php / "composer.json").write_text("{}")
    assert sandbox_commands.image_for(["npm", "test"], str(php)) == "node:22-slim"
    assert sandbox_commands.image_for(["vendor/bin/phpunit"], str(php)) == "php:8.3-cli"
    assert sandbox_commands.image_for(["composer", "test"], str(php)) == "composer:2"
    assert sandbox_commands.image_for(["grep", "-q", "x", "a.php"], str(php)) == "php:8.3-cli", "default: project stack"
    assert sandbox_commands.image_for(["pytest"], str(php)) == "python:3.12-slim"
    plan = sandbox_commands.install_plan(str(php))
    assert [p["stack"] for p in plan] == ["php"] and "--no-scripts" in plan[0]["command"] and "--no-plugins" in plan[0]["command"]

    def raising(*args, **kwargs):
        raise sandbox.SandboxError("Docker is not running.")

    with mock.patch.object(sandbox_commands, "run_in_sandbox", raising):
        out = sandbox_commands.run_sandboxed(str(php), "npm test", 30)
    assert out["exit_code"] == 125 and "Docker is not running" in out["output"], out
    timed = sandbox.SandboxResult(["npm", "test"], "node:22-slim", None, "partial", "", True, 30.0, False)
    with mock.patch.object(sandbox_commands, "run_in_sandbox", lambda *a, **k: timed):
        assert sandbox_commands.run_sandboxed(str(php), "npm test", 30)["exit_code"] == 124


def check_job_to_ai_team(base: Path) -> None:
    os.environ["ASF_CLIENT_WORKSPACES"] = str(base / "workspaces")
    service.HEALTH_CHECK_ONLINE = False
    expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).replace(microsecond=0).isoformat()
    token = _sign_claims({"sub": "founder@example.com", "role": "founder", "exp": expires})
    http = TestClient(app)

    def post(path: str, **body):
        return http.post(f"/mission-control/{path}", json={"token": token, **body}).json()

    original = base / "kopi-shop"
    original.mkdir()
    (original / "package.json").write_text(json.dumps({"name": "kopi", "scripts": {"test": "node test.js"}}))
    (original / "greet.js").write_text("module.exports = () => 'hi';\n")
    (original / ".git").mkdir()
    (original / ".git" / "config").write_text("[core]\n\tfsmonitor = touch /tmp/pwned\n")
    snapshot = {p.relative_to(original).as_posix(): p.read_bytes() for p in original.rglob("*") if p.is_file()}

    client_id = post("clients/create", name="Kopi Shop")["client"]["client_id"]
    codebase_id = post("clients/add-codebase", client_id=client_id, source=str(original))["codebase"]["codebase_id"]
    fix = post("clients/add-job", client_id=client_id, title="Greeting says hi instead of hello", kind="fix")["job"]
    check_only = post("clients/add-job", client_id=client_id, title="Health Check", kind="health_check")["job"]
    detail = post("clients/detail", client_id=client_id)
    provider = detail["ai_provider"]
    jobs = {j["job_id"]: j for j in detail["client"]["jobs"]}
    assert jobs[fix["job_id"]]["can_start_work"] and not jobs[check_only["job_id"]]["can_start_work"]

    start = dict(job_id=fix["job_id"], codebase_id=codebase_id, client_consent=True, ai_provider=provider)
    assert http.post("/mission-control/clients/start-work", json=start).json()["status"] == "unauthorized"
    for missing in ({"client_consent": False}, {"client_consent": "yes"}, {"ai_provider": "someone-else"}):
        refused = post("clients/start-work", **{**start, **missing})
        assert refused["status"] == "invalid-request" and "agreed" in refused["error"], refused
    assert post("clients/start-work", **{**start, "job_id": check_only["job_id"]})["status"] == "invalid-request"
    assert post("clients/start-work", **{**start, "codebase_id": "CB-nope"})["status"] == "invalid-request"

    pod = Pod({"Software Architect": [*finish("p1", PLAN)],
               "Builder": [*write("b1", "greet.js", "module.exports = () => 'hello';\n", "returns hello")],
               "QA Lead": [*finish("q1", PASS)]})
    store = MissionStore(base / "missions")
    fake = FakeSandbox()

    def factory() -> Orca:
        return Orca(chat=pod, store=store)

    def host_run(*args, **kwargs):
        raise AssertionError("a client mission ran a command on this machine")

    with mock.patch.object(api_service, "_orca_factory", factory), \
            mock.patch.object(sandbox_commands, "run_in_sandbox", fake), \
            mock.patch.object(gates, "run_workspace_command", host_run):
        started = post("clients/start-work", **start)
        assert started["status"] == "started", started
        mission_id = started["mission_id"]
        runner.wait_for(mission_id, 60)
        again = post("clients/start-work", **start)
        assert again["status"] == "invalid-request" and "already working" in again["error"], again

        mission = store.load(mission_id)
        assert mission.sandboxed and mission.client["client_name"] == "Kopi Shop", mission.client
        assert mission.status == "awaiting_execution_approval", mission.status
        summary = post("orca/missions")["missions"][0]
        assert summary["client"] == "Kopi Shop" and summary["sandboxed"] is True
        copy = Path(mission.workspace_root)
        assert copy.is_dir() and copy != original and not (copy / ".git").exists(), "the copy has no .git of its own"
        history = copy.parent / "history"
        assert (history / "HEAD").is_file() and history not in copy.parents

        decided = post("orca/decide-execution", mission_id=mission_id, approved=True)
        assert decided["status"] == "ok", decided
        runner.wait_for(mission_id, 60)

    mission = store.load(mission_id)
    assert mission.status == "complete", (mission.status, mission.escalation, mission.events[-3:])
    assert mission.dependencies and mission.dependencies[0]["stack"] == "node" and mission.dependencies[0]["passed"]
    installs = [c for c in fake.calls if c.get("keep_workdir")]
    assert len(installs) == 1 and installs[0]["network_reason"] == "install dependencies"
    assert installs[0]["command"][:2] == ["npm", "install"] and "--ignore-scripts" in installs[0]["command"]
    assert (copy / "node_modules" / "left-pad" / "index.js").is_file(), "installed packages copied back"
    assert installs[0]["source"] == str(copy) and not any(Path(k).exists() for k in fake.kept), "scratch removed"
    tests = [c for c in fake.calls if c["command"] == ["npm", "test"]]
    assert tests and all(c["image"] == "node:22-slim" and c.get("network_reason") is None
                         and c.get("include_dependencies") is True and c["source"] == str(copy) for c in tests), tests

    snapshot_after = {p.relative_to(original).as_posix(): p.read_bytes() for p in original.rglob("*") if p.is_file()}
    assert snapshot_after == snapshot, "the client's original code must never change"
    assert not Path("/tmp/pwned").exists()

    with mock.patch.object(api_service, "_orca_factory", factory):  # the views read the check's mission store
        detail = post("clients/detail", client_id=client_id)["client"]
    job = {j["job_id"]: j for j in detail["jobs"]}[fix["job_id"]]
    assert job["status"] == "in_progress" and job["work"]["mission"]["status"] == "complete", job
    assert job["work"]["ai_provider"] == provider
    changes = post("clients/work-changes", work_id=job["work"]["work_id"])
    assert [f["path"] for f in changes["files"]] == ["greet.js"], changes["files"]
    assert "+module.exports = () => 'hello';" in changes["diff"] and "node_modules" not in changes["diff"]
    assert post("clients/work-changes", work_id="WK-nope")["status"] == "invalid-request"


def check_orca_guard(base: Path) -> None:
    orca = Orca(chat=Pod({}), store=MissionStore(base / "guard"))
    outside = base / "outside"
    outside.mkdir()
    for kwargs in ({"client": {"client_id": "x"}}, {"client_base": base / "area"},
                   {"client": {"client_id": "x"}, "client_base": base / "area"}):
        try:
            orca.start_mission("goal", str(outside), **kwargs)
        except ValueError:
            continue
        raise AssertionError(f"client mission outside its area accepted: {kwargs}")


def check_real_docker(base: Path) -> None:
    if not (sandbox.docker_available() and sandbox.image_present("node:22-slim")):
        print("  (Docker or node:22-slim not available: real sandbox run skipped)")
        return
    project = base / "real-node"
    project.mkdir()
    (project / "package.json").write_text(json.dumps({"name": "t", "scripts": {"test": "node test.js"}}))
    (project / "test.js").write_text("require('assert').strictEqual(require('./lib.js')(), 'hello');\n")
    (project / "lib.js").write_text("module.exports = () => 'hello';\n")
    (project / "node_modules" / "dep").mkdir(parents=True)
    (project / "node_modules" / "dep" / "index.js").write_text("module.exports = 1;\n")
    (project / "test2.js").write_text("require('dep'); require('https').get('https://example.com').on('error', () => process.exit(3));\n")
    passed = sandbox_commands.run_sandboxed(str(project), "npm test", 120)
    assert passed["exit_code"] == 0, passed
    offline = sandbox_commands.run_sandboxed(str(project), "node test2.js", 120)
    assert offline["exit_code"] == 3, f"installed deps visible, network blocked: {offline}"
    (project / "lib.js").write_text("module.exports = () => 'hi';\n")
    assert sandbox_commands.run_sandboxed(str(project), "npm test", 120)["exit_code"] != 0


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp).resolve()
        check_policy_and_images(base)
        check_orca_guard(base)
        check_job_to_ai_team(base)
        check_real_docker(base)
    print("CLIENT WORK CHECK PASSED")


if __name__ == "__main__":
    main()
