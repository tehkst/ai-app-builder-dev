"""Check for lockfile updates in client missions (found in the pilot: an upgrade plan that edited
pnpm-lock.yaml by hand, whose tests would have passed on the old packages because the sandbox has no
network). Builders can't write lockfiles; when a task changes package.json the project's own package
manager updates the lockfile and reinstalls (network on, scripts off) before that task's checks run;
a failed update fails the checks; briefs say so. Fake sandbox, scripted employees, no Docker."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock

from app.platform.container_sandbox import service as sandbox
from app.platform.orca import MissionStore, Orca, gates, sandbox_commands
from app.platform.orca.orca_check import PASS, Pod, finish, write
from app.platform.orca.handoffs import runner_note

HANDOVER = {"summary": "Upgraded left-pad.", "changes": ["left-pad 1.3.0"], "how_to_test": ["Run the tests"], "watch_out": []}
PLAN = {"summary": "Upgrade left-pad.", "tasks": [
    {"title": "Upgrade left-pad", "description": "Bump left-pad to 1.3.0 in package.json.", "specialty": "upgrade",
     "files": ["package.json"], "acceptance_checks": ["npm test"]}]}
OLD_LOCK = "lockfileVersion: '9.0'\nleft-pad: 1.1.0\n"


class FakeSandbox:
    """Installs read package.json from the copy and write a matching lockfile and node_modules, as
    pnpm would; `npm test` passes only when the installed left-pad is 1.3.0."""

    def __init__(self, refresh_fails: bool = False, frozen_fails: bool = False) -> None:
        self.calls: List[Dict[str, Any]] = []
        self.refresh_fails, self.frozen_fails = refresh_fails, frozen_fails

    def __call__(self, source_dir, command, image, **options) -> sandbox.SandboxResult:
        self.calls.append({"command": list(command), "network": options.get("network_reason"), **options})
        base = dict(command=list(command), image=image, timed_out=False, duration_seconds=0.1,
                    network=options.get("network_reason") is not None)
        if options.get("keep_workdir"):
            refresh = "--no-frozen-lockfile" in command
            scratch = Path(tempfile.mkdtemp(prefix="fake-lock-")) / "work"
            scratch.mkdir()
            if not refresh and self.frozen_fails:
                return sandbox.SandboxResult(exit_code=1, stdout="", stderr="ERR_PNPM_OUTDATED_LOCKFILE",
                                             workdir=str(scratch), **base)
            if refresh and self.refresh_fails:
                return sandbox.SandboxResult(exit_code=1, stdout="", stderr="ERR_PNPM_NO_MATCHING_VERSION left-pad@9.9.9",
                                             workdir=str(scratch), **base)
            version = json.loads((Path(source_dir) / "package.json").read_text())["dependencies"]["left-pad"]
            (scratch / "node_modules" / "left-pad").mkdir(parents=True)
            (scratch / "node_modules" / "left-pad" / "VERSION").write_text(version)
            (scratch / "pnpm-lock.yaml").write_text(f"lockfileVersion: '9.0'\nleft-pad: {version}\n")
            return sandbox.SandboxResult(exit_code=0, stdout="Done", stderr="", workdir=str(scratch), **base)
        if command == ["npm", "test"]:
            installed = Path(source_dir) / "node_modules" / "left-pad" / "VERSION"
            ok = installed.is_file() and installed.read_text() == "1.3.0"
            return sandbox.SandboxResult(exit_code=0 if ok else 1, stdout="ok" if ok else "left-pad is old", stderr="", **base)
        return sandbox.SandboxResult(exit_code=0, stdout="", stderr="", **base)


def client_mission(base: Path, name: str, pod: Pod, store: MissionStore):
    area = base / "clients" / name / "work"
    workspace = area / "WK-1" / "code"
    workspace.mkdir(parents=True)
    (workspace / "package.json").write_text(json.dumps({"name": "shop", "dependencies": {"left-pad": "1.1.0"}}))
    (workspace / "pnpm-lock.yaml").write_text(OLD_LOCK)
    orca = Orca(chat=pod, store=store)
    mission = orca.start_mission("Upgrade left-pad", str(workspace), client={"client_id": name, "client_name": name},
                                 client_base=area, ai=("deepseek", "deepseek-v4-pro"))
    return orca, mission, workspace


def run(orca: Orca, mission_id: str, fake: FakeSandbox):
    def host_run(*args, **kwargs):
        raise AssertionError("a client mission ran a command on this machine")

    with mock.patch.object(sandbox_commands, "run_in_sandbox", fake), \
            mock.patch.object(gates, "run_workspace_command", host_run):
        mission = orca.run(mission_id)
        assert mission.status == "awaiting_execution_approval", mission.status
        orca.decide_execution(mission_id, approved=True)
        return orca.run(mission_id)


def check_upgrade_updates_lockfile(base: Path, store: MissionStore) -> None:
    bumped = json.dumps({"name": "shop", "dependencies": {"left-pad": "1.3.0"}})
    pod = Pod({"Software Architect": [*finish("p1", PLAN)],
               # The builder first tries the lockfile by hand (refused), then edits package.json.
               "Upgrade Specialist": [*write("b0", "pnpm-lock.yaml", "left-pad: 1.3.0\n", "edited the lockfile")[:1],
                           *write("b1", "package.json", bumped, "bumped left-pad")],
               "QA Lead": [*finish("q1", PASS)], "Security Reviewer": [*finish("s1", PASS)],
               "Technical Writer": [*finish("w1", HANDOVER)]})
    orca, mission, workspace = client_mission(base, "CL-up", pod, store)
    fake = FakeSandbox()
    mission = run(orca, mission.mission_id, fake)
    assert mission.status == "complete", (mission.status, mission.escalation, mission.events[-3:])
    assert (workspace / "pnpm-lock.yaml").read_text() == "lockfileVersion: '9.0'\nleft-pad: 1.3.0\n", "the package manager's lockfile"
    assert (workspace / "node_modules" / "left-pad" / "VERSION").read_text() == "1.3.0", "reinstalled, old folder replaced"
    installs = [c for c in fake.calls if c.get("keep_workdir")]
    assert [c["command"] for c in installs] == [
        ["corepack", "pnpm", "install", "--frozen-lockfile", "--ignore-scripts"],
        ["corepack", "pnpm", "install", "--no-frozen-lockfile", "--ignore-scripts"]], installs
    assert all(c["network"] and "--ignore-scripts" in c["command"] for c in installs), "network on, scripts off"
    tests = [i for i, c in enumerate(fake.calls) if c["command"] == ["npm", "test"]]
    assert tests and fake.calls.index(installs[1]) < tests[0], "the lockfile is updated before the checks run"
    builder_turns = mission.tasks[0].handoffs
    assert [h["kind"] for h in builder_turns][:2] == ["build", "qa_verdict"], builder_turns
    assert [e for e in mission.events if e["event"] == "dependencies_refreshed"][0]["lockfiles"] == ["pnpm-lock.yaml"]


def check_failed_update_fails_the_checks(base: Path, store: MissionStore) -> None:
    bad = json.dumps({"name": "shop", "dependencies": {"left-pad": "9.9.9"}})
    good = json.dumps({"name": "shop", "dependencies": {"left-pad": "1.3.0"}})
    fail = {"verdict": "FAIL", "evidence": "The package update failed.", "issues": [{"severity": "blocker", "detail": "no 9.9.9"}]}
    pod = Pod({"Software Architect": [*finish("p1", PLAN)],
               "Upgrade Specialist": [*write("b1", "package.json", bad, "bumped"), *write("b2", "package.json", good, "real version")],
               "QA Lead": [*finish("q1", fail), *finish("q2", PASS)], "Security Reviewer": [*finish("s1", PASS)],
               "Technical Writer": [*finish("w1", HANDOVER)]})
    orca, mission, workspace = client_mission(base, "CL-bad", pod, store)
    fake = FakeSandbox(refresh_fails=True)
    with mock.patch.object(sandbox_commands, "run_in_sandbox", fake):
        first = orca.run(mission.mission_id)
        orca.decide_execution(mission.mission_id, approved=True)
        orca.run(mission.mission_id, max_steps=2)  # install, then the first attempt
    task = store.load(mission.mission_id).tasks[0]
    verdict = next(h for h in task.handoffs if h["kind"] == "qa_verdict")
    failed = [c for c in verdict["check_results"] if not c["passed"]]
    assert failed and "--no-frozen-lockfile" in failed[0]["command"] and "NO_MATCHING_VERSION" in failed[0]["output"], failed
    assert (workspace / "pnpm-lock.yaml").read_text() == OLD_LOCK, "a failed update leaves the lockfile alone"
    fake.refresh_fails = False  # the builder fixes the version: the update is tried again
    with mock.patch.object(sandbox_commands, "run_in_sandbox", fake), \
            mock.patch.object(gates, "run_workspace_command", lambda *a, **k: (_ for _ in ()).throw(AssertionError("host"))):
        mission = orca.run(mission.mission_id)
    assert mission.status == "complete", (mission.status, mission.events[-3:])
    assert "1.3.0" in (workspace / "pnpm-lock.yaml").read_text()
    assert first.status == "awaiting_execution_approval"


def check_docker_down_pauses(base: Path, store: MissionStore) -> None:
    """Found in the pilot: launchd's PATH had no `docker`, every check failed with exit 125 and the
    first task used up its attempts. Now the mission pauses before installing; a retried task whose
    install failed installs again first."""
    pod = Pod({"Software Architect": [*finish("p1", PLAN)]})
    orca, mission, workspace = client_mission(base, "CL-down", pod, store)
    orca.run(mission.mission_id)
    orca.decide_execution(mission.mission_id, approved=True)
    with mock.patch.object(sandbox_commands, "sandbox_ready", lambda: False):
        mission = orca.run(mission.mission_id)
    assert mission.status == "paused" and "Start Docker Desktop" in mission.paused_reason, mission.paused_reason
    assert mission.dependencies is None and mission.tasks[0].attempts == 0, "nothing ran, no attempt used"

    mission.status, mission.resume_status = "escalated", None  # an older mission stuck on a failed install
    mission.tasks[0].status, mission.tasks[0].attempts = "escalated", 3
    mission.dependencies = [{"stack": "node", "command": "corepack pnpm install", "passed": False, "output": "Docker is not running."}]
    store.save(mission)
    retried = orca.retry_task(mission.mission_id)
    assert retried.dependencies is None and retried.tasks[0].status == "pending", "the install is tried again first"

    # The earlier attempt had already bumped package.json, so the frozen install fails; the update
    # after the next build installs from the manifest anyway, and the checks pass on the new version.
    (workspace / "package.json").write_text(json.dumps({"name": "shop", "dependencies": {"left-pad": "1.3.0"}}))
    pod.scripts.update({"Upgrade Specialist": [*finish("b9", {"summary": "already bumped", "files_changed": ["package.json"]})],
                        "QA Lead": [*finish("q9", PASS)], "Security Reviewer": [*finish("s9", PASS)],
                        "Technical Writer": [*finish("w9", HANDOVER)]})
    pod.briefings.update({role: [] for role in pod.scripts if role not in pod.briefings})
    fake = FakeSandbox(frozen_fails=True)
    with mock.patch.object(sandbox_commands, "run_in_sandbox", fake):
        mission = orca.run(mission.mission_id)
    assert mission.status == "complete", (mission.status, mission.events[-3:])
    assert [d["passed"] for d in mission.dependencies] == [False, True], mission.dependencies
    assert (workspace / "node_modules" / "left-pad" / "VERSION").read_text() == "1.3.0"


def check_plans_and_briefs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "package.json").write_text("{}")
        (root / "package-lock.json").write_text("{}")
        assert sandbox_commands.refresh_plan(tmp)[0]["command"] == ["npm", "install", "--ignore-scripts", "--no-audit", "--no-fund"]
        (root / "package-lock.json").unlink()
        (root / "yarn.lock").write_text("")
        step = sandbox_commands.refresh_plan(tmp)[0]
        assert "--frozen-lockfile" not in step["command"] and "--ignore-scripts" in step["command"], step
        (root / "package.json").write_text(json.dumps({"packageManager": "yarn@4.1.0"}))
        step = sandbox_commands.refresh_plan(tmp)[0]
        assert "--immutable" not in step["command"] and step["env"]["YARN_ENABLE_SCRIPTS"] == "false", step
        (root / "requirements.txt").write_text("requests==2.32.0\n")
        assert [s["stack"] for s in sandbox_commands.refresh_plan(tmp)] == ["node", "python"]
        before = sandbox_commands.manifest_digest(tmp)
        (root / "README.md").write_text("docs")
        assert sandbox_commands.manifest_digest(tmp) == before, "only dependency files count"
        (root / "requirements.txt").write_text("requests==2.32.3\n")
        assert sandbox_commands.manifest_digest(tmp) != before
    for path in ("pnpm-lock.yaml", "web/package-lock.json", "yarn.lock", "composer.lock", "./npm-shrinkwrap.json"):
        assert sandbox_commands.is_lockfile(path), path
    for path in ("package.json", "src/lock.ts", "docs/pnpm-lock.yaml.md"):
        assert not sandbox_commands.is_lockfile(path), path
    with tempfile.TemporaryDirectory() as tmp:
        from app.platform.nautilus.workspace_tools import build_workspace_tools
        from app.platform.orca.employee_runner import _no_lockfile_writes

        write_tool = _no_lockfile_writes(next(t for t in build_workspace_tools(tmp) if t.name == "write_file"))
        refused = write_tool.handler({"path": "pnpm-lock.yaml", "content": "left-pad: 1.3.0\n"})
        assert refused.startswith("Error: lockfiles are never edited") and not (Path(tmp) / "pnpm-lock.yaml").exists()
        write_tool.handler({"path": "package.json", "content": "{}"})
        assert (Path(tmp) / "package.json").read_text() == "{}"

    class Sandboxed:
        sandboxed = True

    note = runner_note(Sandboxed())  # type: ignore[arg-type]
    assert "pnpm audit" in note and "package.json only" in note, note


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        store = MissionStore(base / "missions")
        check_plans_and_briefs()
        check_upgrade_updates_lockfile(base, store)
        check_failed_update_fails_the_checks(base, store)
        check_docker_down_pauses(base, store)
    print("LOCKFILE CHECK PASSED")


if __name__ == "__main__":
    main()
