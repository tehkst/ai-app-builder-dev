from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class JournalRecord:
    record_id: str
    tenant_id: str
    subject_id: str
    action: str
    target: str
    outcome: str
    metadata: Dict[str, str]

    def belongs_to_tenant(self, tenant_id: str) -> bool:
        return self.tenant_id == tenant_id


class Journal:
    def __init__(self) -> None:
        self._records: List[JournalRecord] = []
        self._ids: set[str] = set()

    def append(self, record: JournalRecord) -> JournalRecord:
        if record.record_id in self._ids:
            raise ValueError("duplicate record")
        self._records.append(record)
        self._ids.add(record.record_id)
        return record

    def list_all(self) -> List[JournalRecord]:
        return list(self._records)

    def list_for_tenant(self, tenant_id: str) -> List[JournalRecord]:
        return [record for record in self._records if record.belongs_to_tenant(tenant_id)]
