"""Durable mission storage: one JSON file per mission, written atomically after every step, so a
mission survives restarts and resumes where it stopped."""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import List, Optional

from app.platform.orca.models import Mission

DEFAULT_STORE_DIR = Path(os.getenv("ORCA_MISSION_DIR", "/tmp/ai-software-factory/orca/missions"))
MISSION_ID_PATTERN = re.compile(r"^ORCA-[A-Z0-9]{6,32}$")


class MissionStore:
    def __init__(self, directory: Optional[Path] = None) -> None:
        self.directory = Path(directory or DEFAULT_STORE_DIR)

    def _path(self, mission_id: str) -> Path:
        if not MISSION_ID_PATTERN.match(mission_id):
            raise ValueError(f"Invalid mission id '{mission_id}'.")
        return self.directory / f"{mission_id}.json"

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
