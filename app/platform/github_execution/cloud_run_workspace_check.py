from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.platform.github_execution import approved_executor


def run_check() -> None:
    observed: list[tuple[list[str], Path]] = []

    def fake_run(command, _env, cwd=approved_executor.REPO_ROOT):
        current = Path(cwd)
        observed.append((command, current))
        if command[:2] == ["git", "clone"]:
            Path(command[-1]).mkdir(parents=True)
        output = " M generated_apps/app-check/main.py" if command[1:3] == ["status", "--porcelain"] else ""
        if command[1:2] == ["rev-parse"]:
            output = "a" * 40
        return SimpleNamespace(stdout=output, stderr="", returncode=0)

    request = {
        "mission_id": "MISSION-CHECK",
        "title": "Cloud Run workspace check",
        "branch_name": "afos-check-branch",
        "commit_message": "test: verify temporary execution",
        "pr_title": "Temporary execution",
        "pr_body": "Check",
        "file_changes": [{
            "path": "generated_apps/app-check/main.py",
            "operation": "write",
            "content": "print('ok')\n",
        }],
    }
    with patch.object(approved_executor, "_run", fake_run), patch.object(
        approved_executor, "_create_pull_request",
        return_value={"url": "https://example.test/pr/1", "number": 1},
    ):
        result = approved_executor._perform_execution(request, "not-a-real-token")
    workspaces = [cwd for command, cwd in observed if command[1:2] != ["clone"]]
    assert workspaces and all(path != approved_executor.REPO_ROOT for path in workspaces)
    assert any(command[1:2] == ["clone"] for command, _ in observed)
    assert any(command[1:2] == ["push"] for command, _ in observed)
    assert result["commit"] == "a" * 40
    assert not workspaces[0].parent.exists()
    print("CLOUD RUN GITHUB WORKSPACE CHECK PASSED")


if __name__ == "__main__":
    run_check()
