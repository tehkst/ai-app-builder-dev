"""Mission Control as an always-on Mac service.

    python -m app.platform.ops setup        type the founder login (once); nothing is printed back
    python -m app.platform.ops install      start at login, restart on crash, nightly backup at 02:30
    python -m app.platform.ops status       is it running, where its data, logs and backups are
    python -m app.platform.ops restart      after pulling new code
    python -m app.platform.ops backup       make a backup now
    python -m app.platform.ops backups      list backups and check each one
    python -m app.platform.ops restore <folder>   put a backup back (stop the service first)
    python -m app.platform.ops uninstall    stop the service (data and backups stay)
    python -m app.platform.ops serve        what the LaunchAgent runs (127.0.0.1 only)
"""
from __future__ import annotations

import argparse
import getpass
import os
import secrets
import subprocess
import sys
import urllib.request
from pathlib import Path

from app.platform.ops import backup as backups
from app.platform.ops import mac_service as svc


def cmd_setup(args: argparse.Namespace) -> int:
    home = svc.asf_home()
    path = home / "mission-control.env"
    current = svc.read_env_file(path)
    if current.get("FOUNDER_EMAIL") and current.get("FOUNDER_PASSWORD") and not args.force:
        print(f"Login already set in {path} (use --force to replace it).")
        return 0
    email = input("Founder email for Mission Control: ").strip()
    if "@" not in email:
        print("That doesn't look like an email address; nothing was saved.")
        return 1
    password = getpass.getpass("Choose a Mission Control password (12+ characters, not shown): ")
    if len(password) < 12:
        print("Use at least 12 characters; nothing was saved.")
        return 1
    if getpass.getpass("Type it again: ") != password:
        print("The two passwords differ; nothing was saved.")
        return 1
    values = dict(current)
    values.update({"FOUNDER_EMAIL": email, "FOUNDER_PASSWORD": password,
                   "MISSION_CONTROL_SESSION_SECRET": current.get("MISSION_CONTROL_SESSION_SECRET") or secrets.token_urlsafe(48)})
    svc.write_env_file(path, values)
    print(f"Saved to {path} (readable only by you). Next: python -m app.platform.ops install")
    return 0


def _health(port: int) -> str:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=3) as response:
            return f"answering on http://127.0.0.1:{port} (HTTP {response.status})"
    except Exception as exc:
        return f"not answering on port {port} ({type(exc).__name__})"


def cmd_install(args: argparse.Namespace) -> int:
    try:
        written = svc.install(port=args.port, keep_awake=not args.allow_sleep)
    except RuntimeError as exc:
        print(exc)
        return 1
    for path in written:
        print(f"Installed {path}")
    print(f"Mission Control will open at http://127.0.0.1:{args.port}/mission-control; logs in {svc.asf_home() / 'logs'}")
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    for path in svc.uninstall():
        print(f"Removed {path}")
    print(f"Service stopped. Data and backups are untouched in {svc.asf_home()}.")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    home = svc.asf_home()
    uid = os.getuid()
    for label in (svc.SERVICE_LABEL, svc.BACKUP_LABEL):
        loaded = subprocess.run(["launchctl", "print", f"gui/{uid}/{label}"], capture_output=True, text=True).returncode == 0
        print(f"{label}: {'loaded' if loaded else 'not installed'}")
    print(f"Mission Control: {_health(args.port)}")
    missing = svc.missing_login(home)
    print(f"Founder login: {'set' if not missing else 'missing ' + ', '.join(missing) + ' (run setup)'}")
    print(f"Data: {home / 'data'}\nLogs: {home / 'logs'}")
    found = backups.list_backups(home)
    print(f"Backups: {len(found)} in {backups.backup_root(home)}" + (f", newest {found[-1].name}" if found else ""))
    return 0


def cmd_backup(args: argparse.Namespace) -> int:
    target = backups.run_backup()
    problems = backups.verify(target)
    print(f"Backup {target}: " + ("verified" if not problems else "PROBLEMS: " + "; ".join(problems)))
    return 1 if problems else 0


def cmd_backups(args: argparse.Namespace) -> int:
    found = backups.list_backups()
    if not found:
        print(f"No backups yet in {backups.backup_root()}.")
    for path in found:
        problems = backups.verify(path)
        size = sum(f.stat().st_size for f in path.iterdir() if f.is_file())
        print(f"{path.name}  {size / 1_000_000:.1f} MB  " + ("ok" if not problems else "; ".join(problems)))
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    folder = Path(args.backup)
    if not folder.is_absolute():
        folder = backups.backup_root() / folder
    if subprocess.run(["launchctl", "print", f"gui/{os.getuid()}/{svc.SERVICE_LABEL}"], capture_output=True).returncode == 0:
        print("Stop the service first: python -m app.platform.ops uninstall")
        return 1
    try:
        aside = backups.restore(folder)
    except RuntimeError as exc:
        print(exc)
        return 1
    print(f"Restored {folder.name}. The data it replaced is kept in {aside}.")
    return 0


def cmd_restart(args: argparse.Namespace) -> int:
    print("Restarted." if svc.restart() else "The service isn't installed; run install.")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    home = svc.asf_home()
    missing = svc.missing_login(home)
    if missing:
        print("mission-control.env is missing " + ", ".join(missing) + "; run `python -m app.platform.ops setup`.", file=sys.stderr)
        return 1
    for sub in ("data", "logs", "client-workspaces"):
        (home / sub).mkdir(parents=True, exist_ok=True, mode=0o700)
    command = [sys.executable, "-m", "uvicorn", "app.platform.server:app", "--host", "127.0.0.1", "--port", str(args.port)]
    os.chdir(svc.REPO_ROOT)
    os.execve(sys.executable, command, svc.serve_environment(home))
    return 0  # not reached


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.platform.ops", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    setup = sub.add_parser("setup")
    setup.add_argument("--force", action="store_true")
    setup.set_defaults(fn=cmd_setup)
    for name, fn in (("install", cmd_install), ("status", cmd_status), ("serve", cmd_serve)):
        p = sub.add_parser(name)
        p.add_argument("--port", type=int, default=svc.DEFAULT_PORT)
        if name == "install":
            p.add_argument("--allow-sleep", action="store_true", help="don't keep the Mac awake while the service runs")
        p.set_defaults(fn=fn)
    for name, fn in (("uninstall", cmd_uninstall), ("backup", cmd_backup), ("backups", cmd_backups), ("restart", cmd_restart)):
        sub.add_parser(name).set_defaults(fn=fn)
    restore = sub.add_parser("restore")
    restore.add_argument("backup", help="backup folder name (from `backups`) or a full path")
    restore.set_defaults(fn=cmd_restore)
    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
