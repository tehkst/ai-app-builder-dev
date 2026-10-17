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

import os
import re
import shutil
import subprocess
import tempfile
import threading
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
OUTPUT_LIMIT = 64_000  # bytes of each stream kept (the tail); the rest is dropped while streaming
UNPRIVILEGED_ID = 1000  # used when the host process itself runs as root
# Hard ceilings: callers may lower limits, never remove them (Docker reads 0/-1 as "unlimited").
MAX_CPUS = 4.0
MEMORY_BYTES = (64 * 2**20, 8 * 2**30)
PIDS_RANGE = (16, 4096)
TIMEOUT_RANGE = (1, 3600)


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


class _TailBuffer:
    """Reads a stream in a thread, keeping only the last OUTPUT_LIMIT bytes (bounded host memory)."""

    def __init__(self, stream) -> None:
        self.data = bytearray()
        self.dropped = 0
        self.thread = threading.Thread(target=self._pump, args=(stream,), daemon=True)
        self.thread.start()

    def _pump(self, stream) -> None:
        for chunk in iter(lambda: stream.read(8192), b""):
            self.data += chunk
            if len(self.data) > OUTPUT_LIMIT:
                excess = len(self.data) - OUTPUT_LIMIT
                self.dropped += excess
                del self.data[:excess]
        stream.close()

    def text(self) -> str:
        self.thread.join(timeout=10)
        body = self.data.decode("utf-8", "replace")
        return (f"...[{self.dropped} bytes of output dropped]...\n" + body) if self.dropped else body


def _validate_limits(cpus: str, memory: str, pids: int, timeout_seconds: int) -> None:
    try:
        cpu_value = float(cpus)
    except ValueError:
        raise SandboxError(f"cpus must be a number, got {cpus!r}.")
    if not 0 < cpu_value <= MAX_CPUS:
        raise SandboxError(f"cpus must be above 0 and at most {MAX_CPUS}.")
    match = re.fullmatch(r"(\d+)([kmg])", str(memory).lower())
    size = int(match.group(1)) * {"k": 2**10, "m": 2**20, "g": 2**30}[match.group(2)] if match else 0
    if not MEMORY_BYTES[0] <= size <= MEMORY_BYTES[1]:
        raise SandboxError("memory must look like 512m or 2g, between 64m and 8g.")
    if not isinstance(pids, int) or not PIDS_RANGE[0] <= pids <= PIDS_RANGE[1]:
        raise SandboxError(f"pids must be an integer from {PIDS_RANGE[0]} to {PIDS_RANGE[1]}.")
    if not isinstance(timeout_seconds, int) or not TIMEOUT_RANGE[0] <= timeout_seconds <= TIMEOUT_RANGE[1]:
        raise SandboxError(f"timeout_seconds must be from {TIMEOUT_RANGE[0]} to {TIMEOUT_RANGE[1]}.")


def _sandbox_identity(workdir: Path) -> str:
    """Run as the owner of the copy so the code can edit it (Linux), but never as root."""
    uid, gid = os.getuid(), os.getgid()
    if uid != 0:
        return f"{uid}:{gid}"
    for path in [workdir, *workdir.rglob("*")]:  # host runs as root: hand the copy to an unprivileged id
        os.lchown(path, UNPRIVILEGED_ID, UNPRIVILEGED_ID)
    return f"{UNPRIVILEGED_ID}:{UNPRIVILEGED_ID}"


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
    _validate_limits(cpus, memory, pids, timeout_seconds)
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
        "--user", _sandbox_identity(workdir),
        "-v", f"{workdir}:/work:rw", "-w", "/work",
        "-e", "HOME=/tmp", "-e", "CI=true",
    ]
    for key, value in (env or {}).items():
        args += ["-e", f"{key}={value}"]
    args += [image, *command]

    started = time.monotonic()
    timed_out = False
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = _TailBuffer(proc.stdout), _TailBuffer(proc.stderr)
    try:
        exit_code: Optional[int] = proc.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        subprocess.run(["docker", "kill", name], capture_output=True, timeout=30)
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
        exit_code = None
    stdout, stderr = out.text(), err.text()
    duration = round(time.monotonic() - started, 2)
    if not keep_workdir:
        shutil.rmtree(scratch, ignore_errors=True)
    return SandboxResult(
        command=list(command), image=image, exit_code=exit_code, stdout=stdout, stderr=stderr,
        timed_out=timed_out, duration_seconds=duration, network=network,
        workdir=str(workdir) if keep_workdir else None, limits=limits,
    )
