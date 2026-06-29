from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Migration:
    migration_id: str
    description: str
    safe_to_repeat: bool


MIGRATIONS = [
    Migration("0001_base", "Base data layer marker", True),
]


def list_migrations() -> List[Migration]:
    return list(MIGRATIONS)


def migration_ids() -> List[str]:
    return [migration.migration_id for migration in MIGRATIONS]
