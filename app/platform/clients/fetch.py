"""Get a client's code onto this machine, read-only, without running anything from it.

- Git: https only (no ssh, file://, ext::), default branch only, no submodules, no hooks, no Git
  LFS downloads, no terminal prompts, 10-minute limit. For private GitHub repos the read-only import
  token from Settings -> Credentials (GITHUB_IMPORT_TOKEN) is handed to git through GIT_ASKPASS and
  an environment variable, so it never appears on a command line or in the stored URL.
- Local folder: scanned where it is (Health Checks only read files); never copied or changed.
"""
from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path
from contextlib import contextmanager
from typing import Dict, Iterator, Optional, Tuple
from urllib.parse import urlparse

CLONE_TIMEOUT = 600


class FetchError(ValueError):
    pass


def workspaces_root() -> Path:
    root = Path(os.getenv("ASF_CLIENT_WORKSPACES") or Path.home() / ".ai-software-factory" / "client-workspaces")
    root.mkdir(parents=True, exist_ok=True)
    return root


def classify_source(source: str) -> Tuple[str, str]:
    """('git_url', clean https URL) or ('local_folder', absolute path). Refuses anything else."""
    source = (source or "").strip()
    if source.startswith("https://"):
        parsed = urlparse(source)
        if parsed.username or parsed.password or "@" in parsed.netloc:
            raise FetchError("Don't put credentials in the URL; private GitHub repos use the import token in Settings.")
        if not parsed.netloc or not re.fullmatch(r"[A-Za-z0-9._~/\-]+", parsed.path or "/"):
            raise FetchError("That doesn't look like a repository URL.")
        return "git_url", f"https://{parsed.netloc}{parsed.path}".rstrip("/")
    if source.startswith(("http://", "ssh://", "git@", "file://", "ext::")) or "::" in source:
        raise FetchError("Only https:// Git URLs or a folder on this Mac are accepted.")
    path = Path(source).expanduser()
    if not path.is_absolute() or not path.is_dir():
        raise FetchError("Give an https:// Git URL or the full path of an existing folder on this Mac.")
    resolved = path.resolve()
    if resolved in {Path("/"), Path.home().resolve()}:
        raise FetchError("Choose the project's own folder, not the whole disk or home folder.")
    return "local_folder", str(resolved)


@contextmanager
def git_auth_env(url: str, token: Optional[str] = None) -> Iterator[Dict[str, str]]:
    """Environment for a git command that talks to `url`: no inherited GIT_* settings, no prompts,
    no LFS downloads and, for github.com with a token, the token handed over through GIT_ASKPASS
    and an environment variable (never on the command line, never stored)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update({"GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1", "GCM_INTERACTIVE": "never",
                "GIT_CONFIG_NOSYSTEM": "1"})
    askpass_dir = None
    try:
        if token and urlparse(url).netloc.lower() == "github.com":
            askpass_dir = tempfile.mkdtemp(prefix="asf-askpass-")
            script = Path(askpass_dir, "askpass.sh")
            script.write_text('#!/bin/sh\ncase "$1" in Username*) echo x-access-token ;; *) echo "$ASF_GIT_TOKEN" ;; esac\n')
            script.chmod(stat.S_IRWXU)
            env.update({"GIT_ASKPASS": str(script), "ASF_GIT_TOKEN": token})
        yield env
    finally:
        if askpass_dir:
            shutil.rmtree(askpass_dir, ignore_errors=True)


def clone(url: str, dest: Path, token: Optional[str] = None) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with git_auth_env(url, token) as env:
        args = ["git", "-c", "protocol.allow=never", "-c", "protocol.https.allow=always", "-c", "core.hooksPath=/dev/null",
                "-c", "credential.helper=", "clone", "--single-branch", "--no-recurse-submodules", "--quiet", url, str(dest)]
        try:
            done = subprocess.run(args, env=env, capture_output=True, text=True, timeout=CLONE_TIMEOUT)
        except subprocess.TimeoutExpired:
            shutil.rmtree(dest, ignore_errors=True)
            raise FetchError("Cloning took longer than 10 minutes and was stopped.")
        if done.returncode != 0:
            shutil.rmtree(dest, ignore_errors=True)
            message = (done.stderr or "").strip().splitlines()[-1:] or ["git clone failed"]
            raise FetchError(message[0].replace(token or "\0", "***")[:300])
