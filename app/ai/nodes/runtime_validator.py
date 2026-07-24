import subprocess
from pathlib import Path
from typing import Dict, List

from app.ai.state import ProjectState
from app.platform.artifacts.qualification_target import (
    configured_generated_app_path,
)


GENERATED_APPS_DIR = Path("generated_apps")


def run_command(command: List[str], cwd: Path, timeout_seconds: int = 30) -> Dict:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )

        return {
            "command": " ".join(command),
            "return_code": completed.returncode,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
            "passed": completed.returncode == 0,
        }

    except subprocess.TimeoutExpired as error:
        return {
            "command": " ".join(command),
            "return_code": None,
            "stdout": (error.stdout or "")[-4000:] if isinstance(error.stdout, str) else "",
            "stderr": (error.stderr or "")[-4000:] if isinstance(error.stderr, str) else "",
            "passed": False,
            "error": f"Command timed out after {timeout_seconds} seconds",
        }

    except Exception as error:
        return {
            "command": " ".join(command),
            "return_code": None,
            "stdout": "",
            "stderr": str(error),
            "passed": False,
            "error": str(error),
        }


def runtime_validator_node(state: ProjectState) -> ProjectState:
    project_id = state["project_id"]
    project_dir = configured_generated_app_path() or GENERATED_APPS_DIR / project_id
    backend_dir = project_dir / "backend"

    checks = []

    if not backend_dir.exists():
        return {
            **state,
            "runtime_report": {
                "passed": False,
                "checks": [],
                "issues": [
                    {
                        "severity": "high",
                        "issue": f"Generated backend directory does not exist: {backend_dir}",
                    }
                ],
            },
            "current_step": "runtime_validation_failed",
        }

    compile_result = run_command(
        ["python3", "-m", "compileall", "-q", "."],
        cwd=backend_dir,
        timeout_seconds=30,
    )
    checks.append({"name": "python_compileall", **compile_result})

    passed = all(check.get("passed") for check in checks)
    issues = []

    for check in checks:
        if not check.get("passed"):
            issues.append(
                {
                    "severity": "high",
                    "check": check.get("name"),
                    "issue": "Runtime validation check failed",
                    "stderr": check.get("stderr", ""),
                    "stdout": check.get("stdout", ""),
                }
            )

    return {
        **state,
        "runtime_report": {
            "passed": passed,
            "checks": checks,
            "issues": issues,
        },
        "current_step": "runtime_validation_passed" if passed else "runtime_validation_failed",
    }
