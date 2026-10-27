"""Run Mission Control as an always-on macOS service, with daily backups (production item 7).

Everything the service owns lives under ASF_HOME (default ~/.ai-software-factory):

    data/platform.db, data/customers.db   the service's own databases (never the repo's app.db)
    client-workspaces/                    clients' code, Health Check reports and AI-team copies
    logs/                                 service and backup logs
    backups/                              daily backups (ASF_BACKUP_DIR can point at an external or iCloud folder)
    mission-control.env                   founder login and session secret (mode 600, typed by the founder)
    vault.key                             encrypts keys saved in Settings (mode 600, made on the first save)
    ai-keys.env                           AI and GitHub keys (mode 600, typed by the founder)

Two LaunchAgents (per user, no admin rights):
- com.aisoftwarefactory.mission-control: starts at login, restarts after a crash, keeps the Mac awake
  while it runs on mains power (`caffeinate -is`), serves on 127.0.0.1 only;
- com.aisoftwarefactory.backup: every night at 02:30 (launchd runs a missed run after wake).

Secrets never go into the plists (they only point at the env files) and are never printed.
"""
from __future__ import annotations

import os
import plistlib
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
SERVICE_LABEL = "com.aisoftwarefactory.mission-control"
BACKUP_LABEL = "com.aisoftwarefactory.backup"
DEFAULT_PORT = 8000
ENV_FILES = ("mission-control.env", "ai-keys.env")
REQUIRED_LOGIN = ("FOUNDER_EMAIL", "FOUNDER_PASSWORD", "MISSION_CONTROL_SESSION_SECRET")


def asf_home() -> Path:
    return Path(os.getenv("ASF_HOME") or Path.home() / ".ai-software-factory")


def agents_dir() -> Path:
    return Path(os.getenv("ASF_LAUNCH_AGENTS_DIR") or Path.home() / "Library" / "LaunchAgents")


def service_environment(home: Optional[Path] = None) -> Dict[str, str]:
    """Where the service keeps its data. Both database variables are always set: if either were
    missing the app would fall back to files in the repo folder (including app.db)."""
    home = home or asf_home()
    data = home / "data"
    return {
        "ASF_HOME": str(home),
        "PLATFORM_DATABASE_URL": f"sqlite:///{data / 'platform.db'}",
        "DATABASE_URL": f"sqlite+aiosqlite:///{data / 'customers.db'}",
        "ASF_CLIENT_WORKSPACES": str(home / "client-workspaces"),
        "ORCA_AUTO_RESUME": "1",
        # Keys saved in Settings are encrypted with this key (no Cloud KMS on the Mac). Never backed up.
        "ASF_VAULT_KEY_FILE": str(home / "vault.key"),
    }


def read_env_file(path: Path) -> Dict[str, str]:
    """KEY=value lines (optionally `export KEY=value`); comments and blanks ignored. Never logged."""
    values: Dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return values
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.removeprefix("export ").partition("=")
        try:  # shell quoting, as write_env_file writes it and `source` reads it
            parts = shlex.split(value)
            values[key.strip()] = parts[0] if parts else ""
        except ValueError:
            values[key.strip()] = value.strip().strip("'\"")
    return values


def write_env_file(path: Path, values: Dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write("# Mission Control service login. Readable only by you; never committed or backed up.\n")
        for key, value in values.items():
            handle.write(f"{key}={shlex.quote(value)}\n")
    os.chmod(path, 0o600)


def missing_login(home: Optional[Path] = None) -> List[str]:
    values = read_env_file((home or asf_home()) / "mission-control.env")
    return [key for key in REQUIRED_LOGIN if not values.get(key)]


def render_service_plist(python: str, home: Path, port: int = DEFAULT_PORT, keep_awake: bool = True) -> bytes:
    serve = [python, "-m", "app.platform.ops", "serve", "--port", str(port)]
    return plistlib.dumps({
        "Label": SERVICE_LABEL,
        "ProgramArguments": (["/usr/bin/caffeinate", "-is"] + serve) if keep_awake else serve,
        "WorkingDirectory": str(REPO_ROOT),
        "EnvironmentVariables": {"ASF_HOME": str(home), "PYTHONUNBUFFERED": "1"},
        "RunAtLoad": True,
        "KeepAlive": {"SuccessfulExit": False, "Crashed": True},
        "ThrottleInterval": 10,
        "ProcessType": "Interactive",
        "StandardOutPath": str(home / "logs" / "mission-control.log"),
        "StandardErrorPath": str(home / "logs" / "mission-control.err.log"),
    })


def render_backup_plist(python: str, home: Path, hour: int = 2, minute: int = 30) -> bytes:
    return plistlib.dumps({
        "Label": BACKUP_LABEL,
        "ProgramArguments": [python, "-m", "app.platform.ops", "backup"],
        "WorkingDirectory": str(REPO_ROOT),
        "EnvironmentVariables": {"ASF_HOME": str(home), "PYTHONUNBUFFERED": "1"},
        "StartCalendarInterval": {"Hour": hour, "Minute": minute},
        "StandardOutPath": str(home / "logs" / "backup.log"),
        "StandardErrorPath": str(home / "logs" / "backup.err.log"),
    })


def _launchctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["launchctl", *args], capture_output=True, text=True, timeout=30)


def install(port: int = DEFAULT_PORT, keep_awake: bool = True, python: Optional[str] = None, load: bool = True) -> List[Path]:
    """Write both LaunchAgents and (re)load them. Needs the founder login in mission-control.env."""
    home = asf_home()
    missing = missing_login(home)
    if missing:
        raise RuntimeError("Run `python -m app.platform.ops setup` first; mission-control.env is missing " + ", ".join(missing))
    for sub in ("data", "logs", "backups", "client-workspaces"):
        (home / sub).mkdir(parents=True, exist_ok=True, mode=0o700)
    python = python or sys.executable
    written = []
    for label, content in ((SERVICE_LABEL, render_service_plist(python, home, port, keep_awake)),
                           (BACKUP_LABEL, render_backup_plist(python, home))):
        path = agents_dir() / f"{label}.plist"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        written.append(path)
        if load:
            domain = f"gui/{os.getuid()}"
            _launchctl("bootout", f"{domain}/{label}")  # replace an older version if present
            done = _launchctl("bootstrap", domain, str(path))
            if done.returncode != 0:
                raise RuntimeError(f"launchctl could not load {label}: {done.stderr.strip()[:300]}")
    return written


def uninstall(unload: bool = True) -> List[Path]:
    removed = []
    for label in (SERVICE_LABEL, BACKUP_LABEL):
        if unload:
            _launchctl("bootout", f"gui/{os.getuid()}/{label}")
        path = agents_dir() / f"{label}.plist"
        if path.exists():
            path.unlink()
            removed.append(path)
    return removed


def restart() -> bool:
    return _launchctl("kickstart", "-k", f"gui/{os.getuid()}/{SERVICE_LABEL}").returncode == 0


# launchd starts the service with PATH=/usr/bin:/bin:/usr/sbin:/sbin, where `docker` isn't found
# (Docker Desktop links it into /usr/local/bin; Homebrew uses /opt/homebrew/bin). Found in the pilot:
# the first client mission that ran code reported "Docker is not running" while Docker was up.
TOOL_DIRS = ("/usr/local/bin", "/opt/homebrew/bin", "/Applications/Docker.app/Contents/Resources/bin")


def service_path(current: str) -> str:
    """The PATH the service runs with: the tool folders first (when missing), then the given PATH."""
    parts = [p for p in current.split(os.pathsep) if p]
    return os.pathsep.join([d for d in TOOL_DIRS if d not in parts] + parts)


def serve_environment(home: Optional[Path] = None) -> Dict[str, str]:
    """The environment uvicorn runs with: the service paths, then the founder's env files."""
    home = home or asf_home()
    env = dict(os.environ)
    env["PATH"] = service_path(env.get("PATH") or "/usr/bin:/bin:/usr/sbin:/sbin")
    env.update(service_environment(home))
    for name in ENV_FILES:
        env.update(read_env_file(home / name))
    for key, value in service_environment(home).items():
        env.setdefault(key, value)
        if key in ("PLATFORM_DATABASE_URL", "DATABASE_URL", "ASF_CLIENT_WORKSPACES", "ASF_VAULT_KEY_FILE"):
            env[key] = value  # env files can't silently move the service onto other data
    return env
