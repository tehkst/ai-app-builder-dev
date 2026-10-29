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

Lockfiles are never written by an employee (a lockfile records a checksum for every package, which
an AI can't produce). When a task changes package.json or requirements.txt, `refresh_dependencies`
runs the project's own package manager the same way (network on, scripts off): it rewrites the
lockfile and reinstalls, so the acceptance checks run on the new versions. Found in the pilot: an
upgrade plan that hand-edited pnpm-lock.yaml, whose tests would have passed on the old packages.

The sandbox has no database or other service either. A check that fails only for that reason
(`needs_outside_service`) says nothing about the code: Orca marks it "couldn't run here" instead of
failing the task, and the mission finishes unverified with those checks named. Found in the pilot:
`npm test` also ran integration tests that need Postgres, so a correct upgrade failed three times.
"""
from __future__ import annotations

import hashlib
import json
import re
import shlex
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.platform.container_sandbox import service as sandbox

INSTALL_TIMEOUT_SECONDS = 900
PYTHON_DEPS = ".asf-deps"  # pip --target folder; tests see it through PYTHONPATH
DEPENDENCY_DIRS = ("node_modules", "vendor", PYTHON_DEPS)
LOCKFILES = ("pnpm-lock.yaml", "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "composer.lock")
MANIFESTS = ("package.json", "requirements.txt", "composer.json")
TEST_ENV = {"PYTHONPATH": f"/work/{PYTHON_DEPS}"}
INSTALL_ENV = {"npm_config_cache": "/work/.asf-cache/npm", "COMPOSER_CACHE_DIR": "/work/.asf-cache/composer",
               "COREPACK_HOME": "/work/.asf-cache/corepack", "COREPACK_ENABLE_DOWNLOAD_PROMPT": "0",
               "YARN_CACHE_FOLDER": "/work/.asf-cache/yarn", "npm_config_store_dir": "/work/.asf-cache/pnpm"}
NODE, PYTHON, PHP, COMPOSER = (sandbox.STACK_IMAGES[k] for k in ("node", "python", "php", "composer"))
PROGRAM_IMAGES = {"npm": NODE, "npx": NODE, "node": NODE, "python": PYTHON, "python3": PYTHON, "pytest": PYTHON,
                  "php": PHP, "phpunit": PHP, "vendor/bin/phpunit": PHP, "./vendor/bin/phpunit": PHP, "composer": COMPOSER}

_SERVICE = r"\w*(?:DATABASE|POSTGRES|MYSQL|MONGO|REDIS)\w*"
SERVICE_SIGNS = (  # (pattern in a failed check's output, what the check needed)
    (re.compile(_SERVICE + r"[^\n]{0,120}?\b(?:must be set|is not set|are not set|is required|are required|is missing)"),
     "a database or other service the sandbox doesn't have (its settings aren't set)"),
    (re.compile(r"ECONNREFUSED[^\n]*:(?:5432|3306|6379|27017)\b|Can't reach database server|"
                r"could not connect to server|Is the server running"), "a database the sandbox doesn't have"),
    (re.compile(r"\b(?:ENOTFOUND|EAI_AGAIN)\b|getaddrinfo"), "the internet, which the sandbox doesn't have"),
)

# Replaceable for checks (no Docker needed); production uses the real sandbox.
run_in_sandbox: Callable[..., sandbox.SandboxResult] = sandbox.run_in_sandbox


def sandbox_ready() -> bool:
    """Whether client code can run at all (Docker answering). A replaced sandbox (checks) is ready."""
    return run_in_sandbox is not sandbox.run_in_sandbox or sandbox.docker_available()


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


def needs_outside_service(output: str) -> Optional[str]:
    """What a failed check needed that the sandbox lacks, or None (a real failure)."""
    return next((needed for pattern, needed in SERVICE_SIGNS if pattern.search(output or "")), None)


def project_scripts(workspace: str) -> Dict[str, str]:
    """The project's own package.json scripts, so the architect can pick checks that run offline."""
    try:
        scripts = json.loads((Path(workspace) / "package.json").read_text()).get("scripts") or {}
    except (OSError, ValueError, AttributeError):
        return {}
    return {str(k)[:60]: str(v)[:160] for k, v in list(scripts.items())[:30]} if isinstance(scripts, dict) else {}


RUNS_CODE_SCRIPT = re.compile(r"(?:test|typecheck|type-check|build)(?::[A-Za-z0-9_.-]+)?")


def runs_project_code(command: str) -> bool:
    """A check that runs the project's own tests, type-check or build (not just lint or a grep)."""
    try:
        argv = shlex.split(command)
    except ValueError:
        return False
    program, rest = (argv[0], argv[1:]) if argv else ("", [])
    return (program == "pytest" or (program in ("python", "python3") and rest[:2] in (["-m", "pytest"], ["-m", "unittest"]))
            or (program == "npm" and (rest == ["test"] or (len(rest) == 2 and rest[0] == "run" and bool(RUNS_CODE_SCRIPT.fullmatch(rest[1])))))
            or program in ("phpunit", "vendor/bin/phpunit", "./vendor/bin/phpunit") or (program == "composer" and rest == ["test"]))


def code_checks_available(workspace: str) -> List[str]:
    """Checks of that kind this project has (empty: it has no tests, type-check or build to run)."""
    root = Path(workspace)
    found = [f"npm run {name}" if name != "test" else "npm test" for name in project_scripts(workspace)
             if RUNS_CODE_SCRIPT.fullmatch(name)]
    if (root / "phpunit.xml").is_file() or (root / "phpunit.xml.dist").is_file():
        found.append("vendor/bin/phpunit")
    if (root / "pytest.ini").is_file() or (root / "conftest.py").is_file() or (root / "tests").is_dir() and any(
            (root / "tests").glob("test_*.py")):
        found.append("python -m pytest")
    return found


def install_plan(workspace: str) -> List[Dict[str, Any]]:
    """What to install, from the project's own manifests. Install scripts never run."""
    root, plan = Path(workspace), []
    if (root / "package.json").is_file() and not (root / "node_modules").exists():
        plan.append({"stack": "node", "image": NODE, "folder": "node_modules", **node_install(root)})
    if (root / "composer.json").is_file() and not (root / "vendor").exists():
        plan.append({"stack": "php", "image": COMPOSER, "folder": "vendor",
                     "command": ["composer", "install", "--no-scripts", "--no-plugins", "--no-interaction",
                                 "--no-progress", "--ignore-platform-reqs"]})
    if (root / "requirements.txt").is_file() and not (root / PYTHON_DEPS).exists():
        plan.append({"stack": "python", "image": PYTHON, "folder": PYTHON_DEPS,
                     "command": ["pip", "install", "--no-cache-dir", "--disable-pip-version-check",
                                 "--target", PYTHON_DEPS, "-r", "requirements.txt"]})
    return plan


def node_install(root: Path) -> Dict[str, Any]:
    """Install with the project's own package manager and lockfile (pnpm and Yarn via Corepack)."""
    try:
        declared = str(json.loads((root / "package.json").read_text(encoding="utf-8")).get("packageManager") or "")
    except (ValueError, OSError, AttributeError):
        declared = ""
    if (root / "pnpm-lock.yaml").is_file() or declared.startswith("pnpm@"):
        return {"command": ["corepack", "pnpm", "install", "--frozen-lockfile", "--ignore-scripts"], "env": {}}
    if (root / "yarn.lock").is_file() or declared.startswith("yarn@"):
        major = declared[5:].split(".", 1)[0] if declared.startswith("yarn@") else "1"
        if major.isdigit() and int(major) >= 2:  # Yarn Berry: scripts are switched off by setting
            return {"command": ["corepack", "yarn", "install", "--immutable"],
                    "env": {"YARN_ENABLE_SCRIPTS": "false", "YARN_NODE_LINKER": "node-modules"}}
        return {"command": ["corepack", "yarn", "install", "--frozen-lockfile", "--ignore-scripts", "--non-interactive"], "env": {}}
    npm = ["npm", "ci"] if (root / "package-lock.json").is_file() else ["npm", "install"]
    return {"command": npm + ["--ignore-scripts", "--no-audit", "--no-fund"], "env": {}}


def manifest_digest(workspace: str) -> str:
    """Fingerprint of the files that declare dependencies: a change means the lockfile is out of date."""
    digest = hashlib.sha256()
    for name in MANIFESTS:
        path = Path(workspace) / name
        if path.is_file():
            digest.update(name.encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def is_lockfile(path: str) -> bool:
    return Path(str(path).replace("\\", "/")).name in LOCKFILES


def refresh_plan(workspace: str) -> List[Dict[str, Any]]:
    """After a manifest change: update the lockfile to match it and reinstall (scripts still off).
    Composer is left out: `composer update` without names would upgrade everything."""
    root, plan = Path(workspace), []
    if (root / "package.json").is_file():
        step = node_install(root)
        command = step["command"]
        if command[:3] == ["corepack", "pnpm", "install"]:
            command = ["corepack", "pnpm", "install", "--no-frozen-lockfile", "--ignore-scripts"]
        elif command[:3] == ["corepack", "yarn", "install"]:
            command = [c for c in command if c not in ("--immutable", "--frozen-lockfile")]
        else:
            command = ["npm", "install", "--ignore-scripts", "--no-audit", "--no-fund"]
        env = {**step["env"], "YARN_ENABLE_IMMUTABLE_INSTALLS": "false"} if "yarn" in command else step["env"]
        plan.append({"stack": "node", "image": NODE, "folder": "node_modules", "command": command, "env": env,
                     "files": [f for f in LOCKFILES if f != "composer.lock"]})
    if (root / "requirements.txt").is_file():
        plan.append({"stack": "python", "image": PYTHON, "folder": PYTHON_DEPS,
                     "command": ["pip", "install", "--no-cache-dir", "--disable-pip-version-check",
                                 "--target", PYTHON_DEPS, "-r", "requirements.txt"]})
    return plan


def install_dependencies(workspace: str) -> List[Dict[str, Any]]:
    """Install each stack's dependencies in the sandbox and copy the installed folder back."""
    return _run_installs(workspace, install_plan(workspace))


def refresh_dependencies(workspace: str) -> List[Dict[str, Any]]:
    """Rewrite the lockfile for the changed manifest and reinstall; copies back the new lockfile
    and replaces the installed folder."""
    return _run_installs(workspace, refresh_plan(workspace), refresh=True)


def _run_installs(workspace: str, plan: List[Dict[str, Any]], refresh: bool = False) -> List[Dict[str, Any]]:
    results = []
    for step in plan:
        entry = {"stack": step["stack"], "command": " ".join(step["command"])}
        try:
            result = run_in_sandbox(workspace, step["command"], step["image"], timeout_seconds=INSTALL_TIMEOUT_SECONDS,
                                    memory="4g", network_reason="install dependencies", keep_workdir=True,
                                    env={**INSTALL_ENV, **step.get("env", {})})
        except sandbox.SandboxError as exc:
            results.append({**entry, "passed": False, "output": str(exc)[:1000]})
            continue
        kept: Optional[Path] = Path(result.workdir) if result.workdir else None
        try:
            installed = kept / step["folder"] if kept else None
            if result.passed and installed and installed.is_dir() and not installed.is_symlink():
                target = Path(workspace) / step["folder"]
                if refresh and target.is_dir() and not target.is_symlink():
                    shutil.rmtree(target)
                shutil.copytree(installed, target, symlinks=True)
            changed = []
            for name in step.get("files", []) if result.passed and kept else []:
                new_file, old_file = kept / name, Path(workspace) / name
                if new_file.is_file() and not new_file.is_symlink() and (
                        not old_file.is_file() or new_file.read_bytes() != old_file.read_bytes()):
                    shutil.copyfile(new_file, old_file)
                    changed.append(name)
            output = (result.stdout + "\n" + result.stderr).strip()[-2000:]
            results.append({**entry, "passed": result.passed, "output": output,
                            # what the install matched; a failed one doesn't count, so the next attempt tries again
                            **({"manifests": manifest_digest(workspace)} if result.passed else {}),
                            **({"lockfiles_updated": changed} if refresh else {})})
        finally:
            if kept:
                shutil.rmtree(kept.parent, ignore_errors=True)  # the sandbox's scratch folder
    return results
