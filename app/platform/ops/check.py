"""Check for production item 7, the always-on Mac service and daily backups: the LaunchAgents
start at login, restart on crash and hold no secrets; the service always uses its own databases
(never the repo's app.db); the login file is private; backups are consistent, leave out secrets and
installed packages, are verified by checksum, pruned to the newest N and restored without deleting
anything; interrupted missions resume after a restart, missions waiting for someone don't.
No launchctl calls and no real home folder: everything runs in a temporary ASF_HOME."""
from __future__ import annotations

import json
import os
import plistlib
import sqlite3
import stat
import tarfile
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.platform.ops import backup, mac_service as svc
from app.platform.orca import runner
from app.platform.orca.models import Mission
from app.platform.orca.store import MissionStore

SECRET = "s3cret it's \"quoted\" $HOME"  # never in plists; quotes and $ round-trip


def check_service(home: Path) -> None:
    os.environ["ASF_LAUNCH_AGENTS_DIR"] = str(home / "LaunchAgents")
    try:
        svc.install(load=False)
        raise AssertionError("install needs the founder login first")
    except RuntimeError as exc:
        assert "setup" in str(exc)
    svc.write_env_file(home / "mission-control.env", {"FOUNDER_EMAIL": "f@ops.test", "FOUNDER_PASSWORD": SECRET,
                                                       "MISSION_CONTROL_SESSION_SECRET": "x" * 48})
    assert stat.S_IMODE((home / "mission-control.env").stat().st_mode) == 0o600
    assert svc.missing_login(home) == []
    written = svc.install(port=8123, python="/opt/py/bin/python", load=False)
    assert [p.name for p in written] == [f"{svc.SERVICE_LABEL}.plist", f"{svc.BACKUP_LABEL}.plist"]
    service = plistlib.loads(written[0].read_bytes())
    assert service["ProgramArguments"] == ["/usr/bin/caffeinate", "-is", "/opt/py/bin/python", "-m", "app.platform.ops",
                                           "serve", "--port", "8123"], service["ProgramArguments"]
    assert service["RunAtLoad"] and service["KeepAlive"]["Crashed"] and service["WorkingDirectory"] == str(svc.REPO_ROOT)
    nightly = plistlib.loads(written[1].read_bytes())
    assert nightly["StartCalendarInterval"] == {"Hour": 2, "Minute": 30} and nightly["ProgramArguments"][-1] == "backup"
    for path in written:
        assert SECRET not in path.read_text() and "x" * 48 not in path.read_text(), "plists only point at the env files"
    awake = plistlib.loads(svc.render_service_plist("/py", home, keep_awake=False))
    assert awake["ProgramArguments"][0] == "/py"
    for sub in ("data", "logs", "backups", "client-workspaces"):
        assert (home / sub).is_dir()

    # The service's own databases, whatever the env files or the shell say.
    (home / "ai-keys.env").write_text("DEEPSEEK_API_KEY='k'\nexport DATABASE_URL=sqlite+aiosqlite:///./app.db\n")
    os.environ["PLATFORM_DATABASE_URL"] = "sqlite:///./platform.db"
    env = svc.serve_environment(home)
    assert env["DATABASE_URL"] == f"sqlite+aiosqlite:///{home / 'data' / 'customers.db'}", env["DATABASE_URL"]
    assert env["PLATFORM_DATABASE_URL"] == f"sqlite:///{home / 'data' / 'platform.db'}"
    assert env["DEEPSEEK_API_KEY"] == "k" and env["FOUNDER_PASSWORD"] == SECRET and env["ORCA_AUTO_RESUME"] == "1"
    assert svc.read_env_file(home / "mission-control.env")["FOUNDER_PASSWORD"] == SECRET, "values round-trip"
    # launchd's PATH has no /usr/local/bin, where Docker Desktop puts `docker` (found in the pilot).
    parts = env["PATH"].split(os.pathsep)
    assert {"/usr/local/bin", "/opt/homebrew/bin"} <= set(parts) and "/usr/bin" in parts, env["PATH"]
    assert svc.service_path("/usr/local/bin:/usr/bin").split(os.pathsep).count("/usr/local/bin") == 1, "no duplicates"
    assert [p.name for p in svc.uninstall(unload=False)] == [p.name for p in written]


def _db(path: Path, rows: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE IF NOT EXISTS t (n INTEGER)")
    con.executemany("INSERT INTO t VALUES (?)", [(i,) for i in range(rows)])
    con.commit()
    con.close()


def _rows(path: Path) -> int:
    con = sqlite3.connect(path)
    try:
        return con.execute("SELECT COUNT(*) FROM t").fetchone()[0]
    finally:
        con.close()


def check_backups(home: Path) -> None:
    data = home / "data"
    _db(data / "platform.db", 5)
    _db(data / "customers.db", 3)
    code = home / "client-workspaces" / "CL-1" / "code"
    for rel, text in {"index.php": "<?php\n", ".env": "DB_PASSWORD=p\n", "node_modules/x/i.js": "1",
                      "vendor/a/b.php": "<?php\n", "config/id_rsa": "KEY"}.items():
        (code / rel).parent.mkdir(parents=True, exist_ok=True)
        (code / rel).write_text(text)
    start = datetime(2026, 10, 1, 2, 30, tzinfo=timezone.utc)
    first = backup.run_backup(home, now=start)
    assert backup.verify(first) == [], backup.verify(first)
    assert _rows(first / "platform.db") == 5 and _rows(first / "customers.db") == 3
    with tarfile.open(first / "client-workspaces.tar.gz") as tar:
        names = tar.getnames()
    assert "client-workspaces/CL-1/code/index.php" in names, names
    assert not any(n.endswith((".env", "id_rsa")) or "node_modules" in n or "/vendor" in n for n in names), names
    manifest = json.loads((first / "manifest.json").read_text())
    assert set(manifest["files"]) == {"platform.db", "customers.db", "client-workspaces.tar.gz"}
    assert "ai-keys.env" in manifest["not_included"]
    assert not any(p.name.startswith(".") for p in backup.backup_root(home).iterdir()), "no partial folders left"

    # Tampering and corruption are caught.
    copy = backup.run_backup(home, now=start + timedelta(minutes=1))
    with (copy / "customers.db").open("ab") as handle:
        handle.write(b"junk")
    assert any("checksum" in p for p in backup.verify(copy))

    # Retention: only the newest N complete backups stay; foreign folders are left alone.
    (backup.backup_root(home) / "my-notes").mkdir()
    os.environ["ASF_BACKUP_KEEP"] = "3"
    for day in range(2, 7):
        backup.run_backup(home, now=start + timedelta(days=day))
    kept = [p.name for p in backup.list_backups(home)]
    assert kept == ["20261005T023000Z", "20261006T023000Z", "20261007T023000Z"], kept
    assert (backup.backup_root(home) / "my-notes").is_dir()

    # Restore: the current data is moved aside, never deleted.
    _db(data / "platform.db", 100)
    (code / "index.php").write_text("<?php // changed after the backup\n")
    try:
        backup.restore(copy, home)
        raise AssertionError("a backup that fails verification is never restored")
    except RuntimeError:
        pass
    aside = backup.restore(backup.list_backups(home)[-1], home, now=start + timedelta(days=9))
    assert _rows(data / "platform.db") == 5 and _rows(aside / "platform.db") == 105
    assert (code / "index.php").read_text() == "<?php\n"
    assert (aside / "client-workspaces" / "CL-1" / "code" / "index.php").read_text().startswith("<?php // changed")
    assert (aside / "client-workspaces" / "CL-1" / "code" / ".env").is_file(), "secrets left out of backups stay aside"


class _FakeOrca:
    ran: list = []

    def __init__(self, store: MissionStore) -> None:
        self.store = store

    def run(self, mission_id: str) -> None:
        _FakeOrca.ran.append(mission_id)


def check_resume(base: Path) -> None:
    store = MissionStore(base / "missions")
    cases = {"ORCA-AAAAAAAA0001": ("building", "ws1"), "ORCA-AAAAAAAA0002": ("planning", "ws2"),
             "ORCA-AAAAAAAA0003": ("building", "ws1"),  # same workspace as 0001: never two at once
             "ORCA-AAAAAAAA0004": ("paused", "ws3"), "ORCA-AAAAAAAA0005": ("awaiting_decision", "ws4"),
             "ORCA-AAAAAAAA0006": ("awaiting_execution_approval", "ws5"), "ORCA-AAAAAAAA0007": ("complete", "ws6"),
             "ORCA-AAAAAAAA0008": ("escalated", "ws7")}
    for mission_id, (status, ws) in cases.items():
        store.save(Mission(mission_id, "goal", str(base / ws), status=status))
    resumed = runner.resume_interrupted(lambda: _FakeOrca(store))
    for mission_id in resumed:
        runner.wait_for(mission_id, 5)
    assert resumed == ["ORCA-AAAAAAAA0001", "ORCA-AAAAAAAA0002"], resumed
    assert sorted(_FakeOrca.ran) == resumed
    assert any("resumed_after_restart" in json.dumps(e) for e in store.load("ORCA-AAAAAAAA0001").events)
    assert not any("resumed_after_restart" in json.dumps(e) for e in store.load("ORCA-AAAAAAAA0004").events)


def check_startup_hook() -> None:
    from app.platform.server import resume_interrupted_missions

    os.environ.pop("ORCA_AUTO_RESUME", None)
    called = []
    original = runner.resume_interrupted
    runner.resume_interrupted = lambda factory: called.append(factory) or []
    try:
        resume_interrupted_missions()
        assert called == [], "a dev server or a check never starts AI work on its own"
        os.environ["ORCA_AUTO_RESUME"] = "1"
        resume_interrupted_missions()
        assert len(called) == 1
        runner.resume_interrupted = lambda factory: (_ for _ in ()).throw(RuntimeError("bad mission"))
        resume_interrupted_missions()  # must not raise: Mission Control still starts
    finally:
        runner.resume_interrupted = original
        os.environ.pop("ORCA_AUTO_RESUME", None)


def main() -> None:
    saved = {k: os.environ.get(k) for k in ("ASF_HOME", "ASF_LAUNCH_AGENTS_DIR", "ASF_BACKUP_DIR", "ASF_BACKUP_KEEP",
                                            "PLATFORM_DATABASE_URL")}
    try:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            home = base / "asf-home"
            os.environ["ASF_HOME"] = str(home)
            os.environ.pop("ASF_BACKUP_DIR", None)
            check_service(home)
            check_backups(home)
            check_resume(base)
        check_startup_hook()
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    print("OPS SERVICE CHECK PASSED")


if __name__ == "__main__":
    main()
