from __future__ import annotations

from typing import Iterable, List

from app.platform.work.work_models import WorkItem, WorkNote, WorkStep, WorkSummary


OPEN_STATUSES = {"new", "active", "blocked"}
DONE_STATUS = "done"


def make_item(item_id: str, tenant_id: str, title: str, item_type: str, owner: str, status: str = "active") -> WorkItem:
    return WorkItem(item_id, tenant_id, title, item_type, status, owner)


def make_step(step_id: str, item_id: str, title: str, order: int, status: str = "new") -> WorkStep:
    return WorkStep(step_id, item_id, title, status, order)


def make_note(note_id: str, item_id: str, author: str, body: str) -> WorkNote:
    return WorkNote(note_id, item_id, author, body)


def items_for_tenant(items: Iterable[WorkItem], tenant_id: str) -> List[WorkItem]:
    return [item for item in items if item.tenant_id == tenant_id]


def steps_for_item(steps: Iterable[WorkStep], item_id: str) -> List[WorkStep]:
    return sorted([step for step in steps if step.item_id == item_id], key=lambda step: step.order)


def notes_for_item(notes: Iterable[WorkNote], item_id: str) -> List[WorkNote]:
    return [note for note in notes if note.item_id == item_id]


def summarize_work(items: Iterable[WorkItem], steps: Iterable[WorkStep], notes: Iterable[WorkNote]) -> WorkSummary:
    item_list = list(items)
    step_list = list(steps)
    note_list = list(notes)
    return WorkSummary(
        item_count=len(item_list),
        open_count=len([item for item in item_list if item.status in OPEN_STATUSES]),
        done_count=len([item for item in item_list if item.status == DONE_STATUS]),
        step_count=len(step_list),
        note_count=len(note_list),
    )
