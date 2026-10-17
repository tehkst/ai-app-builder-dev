"""Check for the container sandbox: each safety guarantee proven against a real container.

Uses a small image already on the machine (alpine or redis:7-alpine, both have a POSIX shell). On
GitHub Actions it pulls alpine; locally it never downloads anything and skips if no image or no
Docker is available (so CI on a runner without Docker fails loudly instead of skipping silently).
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from app.platform.container_sandbox.service import SandboxError, docker_available, image_present, run_in_sandbox

CANDIDATES = ("alpine:3.20", "redis:7-alpine")
ON_CI = bool(os.getenv("GITHUB_ACTIONS"))


def pick_image() -> str:
    for image in CANDIDATES:
        if image_present(image):
            return image
    if ON_CI and subprocess.run(["docker", "pull", CANDIDATES[0]], capture_output=True, timeout=300).returncode == 0:
        return CANDIDATES[0]
    return ""


def main() -> None:
    if not docker_available():
        if ON_CI:
            raise SystemExit("Docker is required on CI for the container sandbox check.")
        print("CONTAINER SANDBOX CHECK SKIPPED (Docker not running)")
        return
    image = pick_image()
    if not image:
        print("CONTAINER SANDBOX CHECK SKIPPED (no small test image present; nothing downloaded)")
        return

    def run(script: str, **kwargs):
        return run_in_sandbox(str(source), ["sh", "-c", script], image, extra_images=[image], **kwargs)

    os.environ["ASF_HOST_SECRET_PROBE"] = "host-secret-value"
    with tempfile.TemporaryDirectory() as base:
        source = Path(base, "client-app")
        source.mkdir()
        (source / "app.txt").write_text("original\n")

        net = run("ls /sys/class/net; (wget -q -T 3 -O /dev/null http://1.1.1.1 && echo REACHED) || echo BLOCKED")
        interfaces = net.stdout.split()
        assert "eth0" not in interfaces and "BLOCKED" in interfaces and "REACHED" not in interfaces and not net.network, net.stdout
        who = run("id -u; grep CapEff /proc/self/status")
        uid, caps = who.stdout.split("\n", 1)
        assert uid.strip() != "0" and caps.split()[-1] == "0000000000000000", who.stdout  # not root, no capabilities
        root_fs = run("touch /etc/probe && echo WROTE || echo REFUSED")
        assert "REFUSED" in root_fs.stdout, root_fs.stdout  # read-only root filesystem
        edit = run("echo changed > app.txt && echo new > added.txt && cat app.txt")
        assert edit.passed and edit.stdout.strip() == "changed", edit.stderr
        assert (source / "app.txt").read_text() == "original\n" and not (source / "added.txt").exists()  # original untouched
        kept = run("echo kept > added.txt", keep_workdir=True)
        assert kept.workdir and Path(kept.workdir, "added.txt").read_text().strip() == "kept"  # changes collectable
        leak = run("env")
        assert "host-secret-value" not in leak.stdout and "ASF_HOST_SECRET_PROBE" not in leak.stdout  # no host env
        given = run('echo "$GREETING"', env={"GREETING": "hello"})
        assert given.stdout.strip() == "hello"
        pids = run("cat /sys/fs/cgroup/pids.max 2>/dev/null || echo unknown")
        assert pids.stdout.strip() in {"512", "unknown"}, pids.stdout
        slow = run("sleep 30", timeout_seconds=3)
        assert slow.timed_out and not slow.passed and slow.duration_seconds < 20
        left = subprocess.run(["docker", "ps", "-q", "--filter", "name=asf-sbx-"], capture_output=True, text=True)
        assert not left.stdout.strip(), "a timed-out sandbox must not keep running"
        try:
            run_in_sandbox(str(source), ["true"], "ubuntu:latest")
            raise AssertionError("unapproved images must be refused")
        except SandboxError:
            pass
        noisy = run("yes 'output line' | head -c 5000000; echo; echo END")
        assert noisy.passed and len(noisy.stdout) < 70_000 and "bytes of output dropped" in noisy.stdout
        assert noisy.stdout.rstrip().endswith("END"), "the tail of long output is kept"
        for bad_limits in ({"cpus": "0"}, {"cpus": "99"}, {"memory": "0"}, {"memory": "64g"}, {"pids": -1},
                           {"pids": 100000}, {"timeout_seconds": 0}):
            try:
                run("true", **bad_limits)
                raise AssertionError(f"limits that disable protection must be refused: {bad_limits}")
            except SandboxError:
                pass
        for bad in ("/", str(Path.home())):
            try:
                run_in_sandbox(bad, ["true"], image, extra_images=[image])
                raise AssertionError("copying / or the home folder must be refused")
            except SandboxError:
                pass
    print(f"CONTAINER SANDBOX CHECK PASSED (image {image})")


if __name__ == "__main__":
    sys.exit(main())
