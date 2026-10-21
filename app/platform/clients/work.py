"""Hand a client job to the AI team (step 4a): Orca works on a disposable copy of the client's code.

- **The client's code is never changed.** Each job gets its own copy under
  `<client workspaces>/<client>/work/<work id>/code`, made from the fetched copy (or the local
  folder) without its `.git`, node_modules or vendor folders.
- **History lives outside the copy.** A baseline commit is recorded in `.../history`, a git folder
  next to the copy, and every git command here names it explicitly (`--git-dir`, `--work-tree`, no
  hooks, no fsmonitor). Nothing written inside the copy can change how git behaves on this machine.
- **Every command runs in the container sandbox** (`Mission.sandboxed`, see orca/sandbox_commands.py).
- **The client's code is sent to the AI provider** the founder sees in the confirmation, so starting
  work requires the founder to confirm the client agreed to that; who confirmed and which provider
  are stored with the work.

The changes are shown as a diff against the baseline; delivering them to the client's repository is
step 4b.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.platform.clients.fetch import workspaces_root
from app.platform.orca import runner
from app.platform.orca.models import Mission

WORK_KINDS = ("fix", "feature", "upgrade", "care_plan")
COPY_IGNORE = shutil.ignore_patterns(".git", "node_modules", "vendor", ".venv", "venv", "__pycache__", ".asf-deps")
# Installed packages and caches never count as changes to the client's code.
EXCLUDES = ("node_modules/", "vendor/", ".asf-deps/", ".asf-cache/", "__pycache__/", ".pytest_cache/")
DIFF_LIMIT = 200_000
SAFE_GIT = ["-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false", "-c", "core.autocrlf=false",
            "-c", "commit.gpgsign=false", "-c", "user.name=AI Software Factory", "-c", "user.email=factory@localhost"]


class WorkError(ValueError):
    pass


def work_root() -> Path:
    """Where client-mission copies live (Orca only accepts client missions inside it)."""
    root = workspaces_root()
    return root.resolve()


def current_ai() -> Optional[Tuple[str, str]]:
    """(provider, model) that a client mission started now would be pinned to, or None."""
    from app.platform.runtime.provider_router import default_model, selected_provider

    try:
        provider = selected_provider()
        return provider, default_model(provider)
    except Exception:  # no provider configured
        return None


def provider_label(ai: Optional[Tuple[str, str]] = None) -> str:
    ai = ai or current_ai()
    return f"{ai[0]} ({ai[1]})" if ai else "the configured AI provider"


def _git(git_dir: Path, work_tree: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"})
    done = subprocess.run(["git", *SAFE_GIT, f"--git-dir={git_dir}", f"--work-tree={work_tree}", *args],
                          capture_output=True, text=True, env=env, timeout=300)
    if check and done.returncode != 0:
        raise WorkError(f"git {args[0]} failed: {(done.stderr or done.stdout).strip()[-300:]}")
    return done


def prepare_copy(source: str, client_id: str) -> Dict[str, str]:
    """A fresh copy of the code with a baseline commit in a history folder outside it."""
    source_path = Path(source).resolve()
    if not source_path.is_dir():
        raise WorkError("The client's code is not on this machine any more; fetch it again.")
    work_id = f"WK-{uuid.uuid4().hex[:10]}"
    folder = work_root() / client_id / "work" / work_id
    code, history = folder / "code", folder / "history"
    shutil.copytree(source_path, code, ignore=COPY_IGNORE, symlinks=True)
    try:
        _git(history, code, "init", "--quiet")
        (history / "info").mkdir(parents=True, exist_ok=True)
        (history / "info" / "exclude").write_text("\n".join(EXCLUDES) + "\n")
        _git(history, code, "add", "--all")
        _git(history, code, "commit", "--quiet", "--allow-empty", "--no-verify", "-m", "Baseline: the client's code as received")
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    return {"work_id": work_id, "workspace": str(code), "git_dir": str(history)}


def changes(workspace: str, git_dir: str) -> Dict[str, Any]:
    """What the AI team changed, compared with the baseline: per-file stats and the diff."""
    code, history = Path(workspace), Path(git_dir)
    if not code.is_dir() or not history.is_dir():
        return {"files": [], "diff": "", "truncated": False, "missing": True}
    _git(history, code, "add", "--all", "--intent-to-add")  # new files show up in the diff
    stat = _git(history, code, "diff", "--numstat", "HEAD").stdout
    files: List[Dict[str, Any]] = []
    for line in stat.splitlines():
        added, removed, path = (line.split("\t", 2) + ["", "", ""])[:3]
        files.append({"path": path, "added": None if added == "-" else int(added),
                      "removed": None if removed == "-" else int(removed)})
    diff = _git(history, code, "diff", "--no-color", "--no-ext-diff", "HEAD").stdout
    return {"files": files, "diff": diff[:DIFF_LIMIT], "truncated": len(diff) > DIFF_LIMIT, "missing": False}


def patch(workspace: str, git_dir: str) -> Dict[str, Any]:
    """Everything the AI team changed, as a git patch (bytes; binary files included) that applies to
    the client's code as received."""
    code, history = Path(workspace), Path(git_dir)
    if not code.is_dir() or not history.is_dir():
        raise WorkError("The AI team's copy of the code is no longer on this machine.")
    _git(history, code, "add", "--all", "--intent-to-add")
    names = [n for n in _git(history, code, "diff", "--name-only", "HEAD").stdout.splitlines() if n]
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    done = subprocess.run(["git", *SAFE_GIT, f"--git-dir={history}", f"--work-tree={code}", "diff", "--binary",
                           "--no-color", "--no-ext-diff", "--full-index", "HEAD"], capture_output=True, env=env, timeout=300)
    if done.returncode != 0:
        raise WorkError("git diff failed: " + done.stderr.decode(errors="replace").strip()[-300:])
    return {"patch": done.stdout, "files_changed": len(names), "files": names}


def start_mission(*, goal: str, workspace: str, client: Dict[str, Any], ai: Tuple[str, str]) -> Mission:
    """Start Orca on the copy (execution waits for the founder's decision in Home), pinned to the
    AI provider and model the client agreed to."""
    from app.platform.orca import api_service

    orca = api_service._orca_factory()
    mission = orca.start_mission(goal, workspace, client=client, client_base=work_root() / client["client_id"] / "work",
                                 ai=ai)
    mission.record("started_from_client_job", client=client.get("client_name"), job=client.get("job_id"))
    orca.store.save(mission)
    runner.start_background_run(mission.mission_id, api_service._orca_factory, mission.workspace_root)
    return mission


def mission_view(mission_id: str) -> Optional[Dict[str, Any]]:
    from app.platform.orca import api_service

    mission = api_service._orca_factory().store.load(mission_id)
    if mission is None:
        return None
    return {"mission_id": mission.mission_id, "status": mission.status, "running": runner.is_running(mission.mission_id),
            "execution_approval": mission.execution_approval, "tasks_total": len(mission.tasks),
            "tasks_passed": sum(t.status == "passed" for t in mission.tasks), "paused_reason": mission.paused_reason,
            "escalation": (mission.escalation or {}).get("reason"), "finished": mission.finished,
            "dependencies": [{"stack": d["stack"], "passed": d["passed"]} for d in mission.dependencies or []],
            "handover": mission.handover}
