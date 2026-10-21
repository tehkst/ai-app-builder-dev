"""Commands for client missions run in the container sandbox, never on this machine (step 4a).

A client mission (`Mission.sandboxed`) works on a disposable copy of the client's code. Every
command an employee or an acceptance check runs goes through `run_sandboxed`: a fresh container
on a fresh copy of that workspace, no network, the image that fits the command (npm -> Node,
pytest -> Python, phpunit -> PHP, composer -> Composer). Changes made inside the container are
thrown away; employees change files only through their write tool.

Dependencies are installed once per mission by `install_dependencies` (founder-approved execution
only): network on, package install scripts off, in a container on a copy. Only the installed
folders (node_modules, vendor, .asf-deps) are copied back into the mission workspace, so later
offline test runs can use them. `git` keeps them out of the delivered changes.
"""
from __future__ import annotations

import shlex
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.platform.container_sandbox import service as sandbox

INSTALL_TIMEOUT_SECONDS = 900
PYTHON_DEPS = ".asf-deps"  # pip --target folder; tests see it through PYTHONPATH
DEPENDENCY_DIRS = ("node_modules", "vendor", PYTHON_DEPS)
TEST_ENV = {"PYTHONPATH": f"/work/{PYTHON_DEPS}"}
INSTALL_ENV = {"npm_config_cache": "/work/.asf-cache/npm", "COMPOSER_CACHE_DIR": "/work/.asf-cache/composer"}
NODE, PYTHON, PHP, COMPOSER = (sandbox.STACK_IMAGES[k] for k in ("node", "python", "php", "composer"))
PROGRAM_IMAGES = {"npm": NODE, "npx": NODE, "node": NODE, "python": PYTHON, "python3": PYTHON, "pytest": PYTHON,
                  "php": PHP, "phpunit": PHP, "vendor/bin/phpunit": PHP, "./vendor/bin/phpunit": PHP, "composer": COMPOSER}

# Replaceable for checks (no Docker needed); production uses the real sandbox.
run_in_sandbox: Callable[..., sandbox.SandboxResult] = sandbox.run_in_sandbox


def stack_image(workspace: str) -> str:
    """The image for commands that don't name a runtime (e.g. grep): the project's main stack."""
    root = Path(workspace)
    if (root / "composer.json").is_file():
        return PHP
    if (root / "package.json").is_file():
        return NODE
    return PYTHON


def image_for(argv: List[str], workspace: str) -> str:
    return PROGRAM_IMAGES.get(argv[0]) or stack_image(workspace)


def run_sandboxed(workspace: str, command: str, timeout: int) -> Dict[str, Any]:
    """Same shape as nautilus run_workspace_command: {"exit_code", "output"}."""
    argv = shlex.split(command)
    if not argv:
        return {"exit_code": 2, "output": "Command is empty."}
    try:
        result = run_in_sandbox(workspace, argv, image_for(argv, workspace), timeout_seconds=timeout,
                                env=TEST_ENV, include_dependencies=True)
    except sandbox.SandboxError as exc:
        return {"exit_code": 125, "output": f"The sandbox could not run this command: {exc}"}
    output = (result.stdout + ("\n" + result.stderr if result.stderr else "")).strip()
    if result.timed_out:
        return {"exit_code": 124, "output": (output + f"\nTimed out after {timeout} seconds.").strip()}
    return {"exit_code": result.exit_code, "output": output}


def install_plan(workspace: str) -> List[Dict[str, Any]]:
    """What to install, from the project's own manifests. Install scripts never run."""
    root, plan = Path(workspace), []
    if (root / "package.json").is_file() and not (root / "node_modules").exists():
        npm = ["npm", "ci"] if (root / "package-lock.json").is_file() else ["npm", "install"]
        plan.append({"stack": "node", "image": NODE, "folder": "node_modules",
                     "command": npm + ["--ignore-scripts", "--no-audit", "--no-fund"]})
    if (root / "composer.json").is_file() and not (root / "vendor").exists():
        plan.append({"stack": "php", "image": COMPOSER, "folder": "vendor",
                     "command": ["composer", "install", "--no-scripts", "--no-plugins", "--no-interaction",
                                 "--no-progress", "--ignore-platform-reqs"]})
    if (root / "requirements.txt").is_file() and not (root / PYTHON_DEPS).exists():
        plan.append({"stack": "python", "image": PYTHON, "folder": PYTHON_DEPS,
                     "command": ["pip", "install", "--no-cache-dir", "--disable-pip-version-check",
                                 "--target", PYTHON_DEPS, "-r", "requirements.txt"]})
    return plan


def install_dependencies(workspace: str) -> List[Dict[str, Any]]:
    """Install each stack's dependencies in the sandbox and copy the installed folder back."""
    results = []
    for step in install_plan(workspace):
        entry = {"stack": step["stack"], "command": " ".join(step["command"])}
        try:
            result = run_in_sandbox(workspace, step["command"], step["image"], timeout_seconds=INSTALL_TIMEOUT_SECONDS,
                                    memory="4g", network_reason="install dependencies", keep_workdir=True,
                                    env=INSTALL_ENV)
        except sandbox.SandboxError as exc:
            results.append({**entry, "passed": False, "output": str(exc)[:1000]})
            continue
        kept: Optional[Path] = Path(result.workdir) if result.workdir else None
        try:
            installed = kept / step["folder"] if kept else None
            if result.passed and installed and installed.is_dir() and not installed.is_symlink():
                shutil.copytree(installed, Path(workspace) / step["folder"], symlinks=True)
            output = (result.stdout + "\n" + result.stderr).strip()[-2000:]
            results.append({**entry, "passed": result.passed, "output": output})
        finally:
            if kept:
                shutil.rmtree(kept.parent, ignore_errors=True)  # the sandbox's scratch folder
    return results
