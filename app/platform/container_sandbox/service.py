"""Run client code (install, tests, the app itself) inside a locked-down Docker container.

Roadmap item "container isolation": nothing from a client's codebase runs on the founder's machine
directly. Every run:
- works on a throwaway **copy** of the code (the original is never mounted), deleted afterwards
  unless the caller asks to keep it to collect changes;
- has **no network** unless `network_reason` is given (e.g. "install dependencies");
- runs as a non-root user with all Linux capabilities dropped, no privilege escalation, a
  read-only root filesystem (writable /work copy and a small /tmp only);
- is limited in CPU, memory (no swap), process count and wall-clock time, and is killed on timeout;
- gets **no host environment variables** (so no keys leak in), only an explicit `env`;
- may only use approved images (STACK_IMAGES, or `extra_images` from a check).
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

# Official images per stack, pinned to a version line. Pull them once (with the founder's OK).
STACK_IMAGES = {
    "node": "node:22-slim",
    "python": "python:3.12-slim",
    "php": "php:8.3-cli",
}
COPY_IGNORE = shutil.ignore_patterns(".git", "node_modules", "vendor", ".venv", "venv", "__pycache__", "dist", "build", ".next")
OUTPUT_LIMIT = 64_000  # keep the tail of very chatty output
SANDBOX_USER = "1000:1000"


class SandboxError(RuntimeError):
    """The run was refused before anything started (bad input, image not allowed, Docker missing)."""


@dataclass
class SandboxResult:
    command: List[str]
    image: str
    exit_code: Optional[int]
    stdout: str
    stderr: str
    timed_out: bool
    duration_seconds: float
    network: bool
    workdir: Optional[str] = None  # set only when keep_workdir=True
    limits: Dict[str, str] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


def docker_available() -> bool:
    try:
        return subprocess.run(["docker", "info"], capture_output=True, timeout=20).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def image_present(image: str) -> bool:
    try:
        return subprocess.run(["docker", "image", "inspect", image], capture_output=True, timeout=20).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _tail(text: str) -> str:
    return text if len(text) <= OUTPUT_LIMIT else "...[output truncated]...\n" + text[-OUTPUT_LIMIT:]


def _check_source(source: Path) -> Path:
    source = source.expanduser().resolve()
    if not source.is_dir():
        raise SandboxError(f"Not a folder: {source}")
    if source == Path("/") or source == Path.home().resolve():
        raise SandboxError("Refusing to copy the whole disk or home folder into a sandbox.")
    return source


def run_in_sandbox(
    source_dir: str,
    command: List[str],
    image: str,
    *,
    timeout_seconds: int = 300,
    cpus: str = "2",
    memory: str = "2g",
    pids: int = 512,
    network_reason: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    keep_workdir: bool = False,
    extra_images: Iterable[str] = (),
) -> SandboxResult:
    if not command or not all(isinstance(part, str) and part for part in command):
        raise SandboxError("command must be a non-empty list of strings.")
    allowed = set(STACK_IMAGES.values()) | set(extra_images)
    if image not in allowed:
        raise SandboxError(f"Image {image!r} is not approved; use one of {sorted(allowed)}.")
    if not docker_available():
        raise SandboxError("Docker is not running.")
    if not image_present(image):
        raise SandboxError(f"Image {image!r} is not on this machine yet; pull it first (needs the founder's OK).")
    source = _check_source(Path(source_dir))

    scratch = Path(tempfile.mkdtemp(prefix="asf-sandbox-"))
    workdir = scratch / "work"
    shutil.copytree(source, workdir, ignore=COPY_IGNORE, symlinks=True)
    name = f"asf-sbx-{uuid.uuid4().hex[:12]}"
    network = network_reason is not None
    limits = {"cpus": cpus, "memory": memory, "pids": str(pids), "timeout_seconds": str(timeout_seconds)}
    args = [
        "docker", "run", "--rm", "--name", name,
        "--network", "bridge" if network else "none",
        "--cpus", cpus, "--memory", memory, "--memory-swap", memory, "--pids-limit", str(pids),
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--read-only", "--tmpfs", "/tmp:rw,nosuid,nodev,size=512m",
        "--user", SANDBOX_USER,
        "-v", f"{workdir}:/work:rw", "-w", "/work",
        "-e", "HOME=/tmp", "-e", "CI=true",
    ]
    for key, value in (env or {}).items():
        args += ["-e", f"{key}={value}"]
    args += [image, *command]

    started = time.monotonic()
    timed_out = False
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout_seconds)
        exit_code, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        subprocess.run(["docker", "kill", name], capture_output=True, timeout=30)
        exit_code = None
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
    duration = round(time.monotonic() - started, 2)
    if not keep_workdir:
        shutil.rmtree(scratch, ignore_errors=True)
    return SandboxResult(
        command=list(command), image=image, exit_code=exit_code, stdout=_tail(stdout), stderr=_tail(stderr),
        timed_out=timed_out, duration_seconds=duration, network=network,
        workdir=str(workdir) if keep_workdir else None, limits=limits,
    )
