"""Durable mission storage, written after every step so a mission survives restarts and resumes where
it stopped. `DbMissionStore` (the platform database, step 5b) is the default; `MissionStore` (one JSON
file per mission) is kept for checks and for importing missions saved by older versions."""
from __future__ import annotations

import json
import os
import re
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from app.platform.orca.models import Mission

DEFAULT_STORE_DIR = Path(os.getenv("ORCA_MISSION_DIR", "/tmp/ai-software-factory/orca/missions"))
MISSION_ID_PATTERN = re.compile(r"^ORCA-[A-Z0-9]{6,32}$")


def check_id(mission_id: str) -> str:
    if not MISSION_ID_PATTERN.match(str(mission_id or "")):
        raise ValueError(f"Invalid mission id '{mission_id}'.")
    return mission_id


class MissionStore:
    def __init__(self, directory: Optional[Path] = None) -> None:
        self.directory = Path(directory or DEFAULT_STORE_DIR)

    def _path(self, mission_id: str) -> Path:
        return self.directory / f"{check_id(mission_id)}.json"

    def save(self, mission: Mission) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self._path(mission.mission_id)
        handle, temp_name = tempfile.mkstemp(dir=self.directory, suffix=".tmp")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump(mission.to_dict(), stream, indent=2)
            os.replace(temp_name, target)
        except BaseException:
            Path(temp_name).unlink(missing_ok=True)
            raise

    def load(self, mission_id: str) -> Optional[Mission]:
        path = self._path(mission_id)
        if not path.is_file():
            return None
        return Mission.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list_ids(self) -> List[str]:
        if not self.directory.is_dir():
            return []
        return sorted(p.stem for p in self.directory.glob("ORCA-*.json"))

    def record_activity(self, mission_id: str, employee: str, kind: str, detail: str) -> None:
        """JSON missions (checks, CLI with a folder) don't keep a live feed."""

    def activity(self, mission_id: str, after: int = 0) -> List[dict]:
        return []


class DbMissionStore:
    """Missions in the platform database (step 5b), the default for Mission Control and the runner.
    Same interface as MissionStore, plus a live activity feed. Missions saved by older versions in
    the JSON folder (ORCA_MISSION_DIR) are imported once, the first time missions are listed."""

    _imported: set = set()
    _lock = threading.Lock()
    ACTIVITY_KEEP = 400  # newest lines kept per mission

    def __init__(self, legacy_directory: Optional[Path] = None) -> None:
        self.legacy_directory = Path(legacy_directory or DEFAULT_STORE_DIR)

    @staticmethod
    def _session():
        from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables

        create_platform_tables()
        return PlatformSessionLocal()

    def save(self, mission: Mission) -> None:
        from app.platform.persistence.models import PlatformOrcaMission

        check_id(mission.mission_id)
        data = json.dumps(mission.to_dict())
        with self._lock, self._session() as db:
            row = db.query(PlatformOrcaMission).filter_by(mission_id=mission.mission_id).first()
            if row is None:
                row = PlatformOrcaMission(mission_id=mission.mission_id, created_at=_parse(mission.created_at))
                db.add(row)
            row.status, row.goal, row.data_json = mission.status, mission.goal, data
            row.client_id = (mission.client or {}).get("client_id")
            row.sandboxed, row.updated_at = bool(mission.sandboxed), _parse(mission.updated_at)
            db.commit()

    def load(self, mission_id: str) -> Optional[Mission]:
        from app.platform.persistence.models import PlatformOrcaMission

        check_id(mission_id)
        with self._session() as db:
            row = db.query(PlatformOrcaMission).filter_by(mission_id=mission_id).first()
            data = row.data_json if row else None
        return Mission.from_dict(json.loads(data)) if data else None

    def list_ids(self) -> List[str]:
        from app.platform.persistence.models import PlatformOrcaMission

        self.import_legacy()
        with self._session() as db:
            return sorted(r.mission_id for r in db.query(PlatformOrcaMission.mission_id).all())

    def import_legacy(self) -> int:
        """Copy missions from the old JSON folder into the database (once per folder per process)."""
        key = str(self.legacy_directory.resolve())
        if key in self._imported:
            return 0
        self._imported.add(key)
        legacy = MissionStore(self.legacy_directory)
        imported = 0
        for mission_id in legacy.list_ids():
            try:
                if self.load(mission_id) is None:
                    mission = legacy.load(mission_id)
                    if mission is not None:
                        self.save(mission)
                        imported += 1
            except (ValueError, OSError, TypeError):
                continue  # a broken old file never blocks the list
        return imported

    def record_activity(self, mission_id: str, employee: str, kind: str, detail: str) -> None:
        from app.platform.persistence.models import PlatformOrcaActivity

        with self._session() as db:
            db.add(PlatformOrcaActivity(mission_id=mission_id, employee=employee, kind=kind, detail=detail[:240]))
            db.commit()
            count = db.query(PlatformOrcaActivity).filter_by(mission_id=mission_id).count()
            if count > self.ACTIVITY_KEEP + 50:  # trim in batches, keep the newest
                cutoff = (db.query(PlatformOrcaActivity.id).filter_by(mission_id=mission_id)
                          .order_by(PlatformOrcaActivity.id.desc()).offset(self.ACTIVITY_KEEP).first())
                if cutoff:
                    db.query(PlatformOrcaActivity).filter(PlatformOrcaActivity.mission_id == mission_id,
                                                          PlatformOrcaActivity.id <= cutoff[0]).delete()
                    db.commit()

    def activity(self, mission_id: str, after: int = 0, limit: int = 100) -> List[dict]:
        from app.platform.persistence.models import PlatformOrcaActivity

        with self._session() as db:
            rows = (db.query(PlatformOrcaActivity).filter(PlatformOrcaActivity.mission_id == mission_id,
                                                          PlatformOrcaActivity.id > after)
                    .order_by(PlatformOrcaActivity.id.desc()).limit(limit).all())
            return [{"id": r.id, "employee": r.employee, "kind": r.kind, "detail": r.detail,
                     "at": _utc(r.at)} for r in reversed(rows)]


def _utc(value: Optional[datetime]) -> Optional[str]:
    """SQLite hands back naive datetimes: they are UTC, so say so (the browser shows local time)."""
    if value is None:
        return None
    return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()


def _parse(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)
