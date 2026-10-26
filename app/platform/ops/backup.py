"""Daily backups of the always-on service's data (production item 7).

One backup is a folder backups/<UTC timestamp>/ with:
    platform.db, customers.db     consistent copies made with SQLite's backup API (safe while the service runs)
    client-workspaces.tar.gz      clients' code and reports, without installed packages, caches or secret files
    manifest.json                 what was copied, sizes and SHA-256 of every file (checked by `verify`)

Never backed up: mission-control.env, ai-keys.env, vault.key and secret files in client code (.env, keys,
credentials), so a backup folder in iCloud or on a shared disk holds no passwords or keys.
The newest ASF_BACKUP_KEEP backups (default 14) are kept; older ones are removed by `prune`.
A restore never deletes anything: the current data is moved aside first.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from app.platform.ops.mac_service import asf_home, service_environment

DEFAULT_KEEP = 14
SKIP_DIRS = {"node_modules", "vendor", ".asf-deps", ".asf-cache", "__pycache__", ".pytest_cache", ".venv", "venv"}
DATABASES = ("platform.db", "customers.db")


def backup_root(home: Optional[Path] = None) -> Path:
    return Path(os.getenv("ASF_BACKUP_DIR") or (home or asf_home()) / "backups")


def keep_count() -> int:
    try:
        return max(1, int(os.getenv("ASF_BACKUP_KEEP", DEFAULT_KEEP)))
    except ValueError:
        return DEFAULT_KEEP


def _sqlite_path(url: str) -> Path:
    return Path(url.split(":///", 1)[1])


def _database_paths(home: Path) -> Dict[str, Path]:
    env = service_environment(home)
    return {"platform.db": _sqlite_path(env["PLATFORM_DATABASE_URL"]), "customers.db": _sqlite_path(env["DATABASE_URL"])}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_sqlite(source: Path, target: Path) -> None:
    src = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(str(target))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def _tar_filter(info: tarfile.TarInfo) -> Optional[tarfile.TarInfo]:
    from app.platform.clients.redaction import is_secret_file

    parts = Path(info.name).parts
    if any(part in SKIP_DIRS for part in parts) or is_secret_file(parts[-1]):
        return None
    return info


def run_backup(home: Optional[Path] = None, now: Optional[datetime] = None) -> Path:
    """Make one backup and prune old ones. Returns the new backup folder."""
    home = home or asf_home()
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    root = backup_root(home)
    target = root / stamp
    partial = root / f".{stamp}.partial"
    if partial.exists():
        shutil.rmtree(partial)
    partial.mkdir(parents=True, mode=0o700)
    files: Dict[str, dict] = {}
    for name, source in _database_paths(home).items():
        if source.is_file():
            _copy_sqlite(source, partial / name)
    workspaces = Path(service_environment(home)["ASF_CLIENT_WORKSPACES"])
    if workspaces.is_dir():
        with tarfile.open(partial / "client-workspaces.tar.gz", "w:gz") as tar:
            tar.add(str(workspaces), arcname="client-workspaces", filter=_tar_filter)
    for path in sorted(partial.iterdir()):
        files[path.name] = {"bytes": path.stat().st_size, "sha256": _sha256(path)}
    manifest = {"created_at": stamp, "home": str(home), "files": files,
                "not_included": ["mission-control.env", "ai-keys.env", "vault.key", "secret files in client code",
                                 "installed packages and caches"]}
    (partial / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    partial.rename(target)  # a backup folder only ever appears complete
    prune(home)
    return target


def list_backups(home: Optional[Path] = None) -> List[Path]:
    root = backup_root(home)
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".") and (p / "manifest.json").is_file())


def prune(home: Optional[Path] = None, keep: Optional[int] = None) -> List[Path]:
    """Remove all but the newest `keep` complete backups (only folders this module made)."""
    keep = keep or keep_count()
    backups = list_backups(home)
    removed = backups[:-keep] if len(backups) > keep else []
    for path in removed:
        shutil.rmtree(path)
    return removed


def verify(backup: Path) -> List[str]:
    """Problems with a backup (empty list = every file matches its manifest and the databases open)."""
    try:
        manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"manifest unreadable: {exc}"]
    problems = []
    for name, info in manifest.get("files", {}).items():
        path = backup / name
        if not path.is_file():
            problems.append(f"{name} is missing")
        elif _sha256(path) != info.get("sha256"):
            problems.append(f"{name} does not match its checksum")
        elif name.endswith(".db"):
            con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            try:
                if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    problems.append(f"{name} failed the SQLite integrity check")
            finally:
                con.close()
    return problems


def restore(backup: Path, home: Optional[Path] = None, now: Optional[datetime] = None) -> Path:
    """Put a backup's databases and client workspaces back. Stop the service first. The current
    data/ and client-workspaces/ are moved to before-restore-<time>/, never deleted."""
    home = home or asf_home()
    problems = verify(backup)
    if problems:
        raise RuntimeError("Backup failed verification: " + "; ".join(problems))
    aside = home / f"before-restore-{(now or datetime.now(timezone.utc)).strftime('%Y%m%dT%H%M%SZ')}"
    aside.mkdir(parents=True, mode=0o700)
    databases = _database_paths(home)
    workspaces = Path(service_environment(home)["ASF_CLIENT_WORKSPACES"])
    for name, current in databases.items():
        if current.exists():
            shutil.move(str(current), str(aside / name))
        if (backup / name).is_file():
            current.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup / name, current)
    archive = backup / "client-workspaces.tar.gz"
    if archive.is_file():
        if workspaces.exists():
            shutil.move(str(workspaces), str(aside / "client-workspaces"))
        with tarfile.open(archive, "r:gz") as tar:
            tar.extractall(workspaces.parent, filter="data")
        extracted = workspaces.parent / "client-workspaces"
        if extracted != workspaces:
            extracted.rename(workspaces)
    return aside
