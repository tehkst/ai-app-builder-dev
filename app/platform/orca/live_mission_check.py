"""Live check: a real Orca mission with AI employees on the configured provider.

Builds a tiny FastAPI app in a fresh sandbox workspace, asks Orca to add a /health endpoint
with a unittest, pre-approves execution (the check is the founder here), and verifies the result
independently of Orca. Needs a real API key, so it lives in the ai-integration profile and in the
CI step "Orca live mission"; costs a few cents per run.

    AI_PROVIDER=deepseek python -m app.platform.orca.live_mission_check
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

from app.platform.nautilus.chat_providers import build_chat_fn
from app.platform.nautilus.workspace_tools import run_workspace_command
from app.platform.orca import MissionStore, Orca
from app.platform.runtime.provider_router import default_model, provider_status, selected_provider
from app.platform.services.materialization_sandbox_writer_service import APPROVED_SANDBOX_ROOT_BASE

GOAL = ('Add a GET /health endpoint to the FastAPI app in app/main.py that returns {"status": "ok"}, '
        "with a unittest test case for it in tests/.")
DEMO_FILES = {
    "app/__init__.py": "",
    "app/main.py": 'from fastapi import FastAPI\n\napp = FastAPI(title="Demo")\n\n\n@app.get("/")\n'
                   'def root():\n    return {"message": "Hello from the demo app"}\n',
    "tests/__init__.py": "",
    "tests/test_root.py": "import unittest\n\nfrom fastapi.testclient import TestClient\n\nfrom app.main import app\n\n\n"
                          "class RootTest(unittest.TestCase):\n    def test_root(self):\n"
                          '        self.assertEqual(TestClient(app).get("/").json(), {"message": "Hello from the demo app"})\n',
}
INDEPENDENT_CHECK = "python -m unittest discover -s tests -t ."


def _fail(message: str, mission=None) -> None:
    print(f"ORCA LIVE MISSION FAILED: {message}")
    if mission is not None:
        print(json.dumps({"status": mission.status, "escalation": mission.escalation,
                          "paused_reason": mission.paused_reason, "events": mission.events[-8:]},
                         indent=2, default=str)[:12_000])
    sys.exit(1)


def main() -> None:
    from app.platform.persistence.database import create_platform_tables

    create_platform_tables()
    status = provider_status()
    if not status["api_key_present"]:
        _fail(f"{status['secret_name']} is not configured for provider '{status['provider']}'.")
    provider = status["provider"]
    model = os.getenv("ORCA_LIVE_MODEL") or default_model(selected_provider(provider))
    print(f"Orca live mission: provider={provider} model={model}")

    workspace = APPROVED_SANDBOX_ROOT_BASE / f"orca-live-{uuid.uuid4().hex[:8]}"
    store_dir = Path(tempfile.mkdtemp(prefix="orca-live-missions-"))
    try:
        for relative, content in DEMO_FILES.items():
            target = workspace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        baseline = run_workspace_command(str(workspace), INDEPENDENT_CHECK)
        if baseline["exit_code"] != 0:
            _fail("demo app tests fail before the mission: " + baseline["output"][-2000:])

        orca = Orca(chat=build_chat_fn(provider, model), store=MissionStore(store_dir))
        mission = orca.start_mission(GOAL, str(workspace), execution_approved=True)
        mission = orca.run(mission.mission_id)
        print("  " + json.dumps({"status": mission.status, "tasks": [
            {"id": t.task_id, "title": t.title, "status": t.status, "attempts": t.attempts,
             "checks": t.acceptance_checks} for t in mission.tasks]}))
        if mission.status != "complete":
            _fail(f"mission ended '{mission.status}', expected 'complete'", mission)

        independent = run_workspace_command(str(workspace), INDEPENDENT_CHECK)
        print(f"  independent unittest: exit {independent['exit_code']}")
        if independent["exit_code"] != 0:
            _fail("Orca reported complete but the app's tests fail: " + independent["output"][-2000:], mission)
        probe = run_workspace_command(str(workspace), "grep -rq /health app tests")
        if probe["exit_code"] != 0:
            _fail("no /health route or test found in the workspace", mission)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
        shutil.rmtree(store_dir, ignore_errors=True)
    print("ORCA LIVE MISSION PASSED")


if __name__ == "__main__":
    main()
