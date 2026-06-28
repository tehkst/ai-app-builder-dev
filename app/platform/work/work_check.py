from __future__ import annotations

from app.platform.work.work_flow import run_demo_work
from app.platform.work.work_store import items_for_tenant, notes_for_item, steps_for_item, summarize_work


def main() -> None:
    data = run_demo_work()
    assert len(data.items) == 2, data
    assert len(data.steps) == 3, data
    assert len(data.notes) == 2, data

    tenant_items = items_for_tenant(data.items, "tenant_platform")
    assert len(tenant_items) == 2, tenant_items
    assert items_for_tenant(data.items, "other") == []

    ordered_steps = steps_for_item(data.steps, "work1")
    assert [step.order for step in ordered_steps] == [1, 2, 3], ordered_steps
    assert len(notes_for_item(data.notes, "work1")) == 1

    summary = summarize_work(data.items, data.steps, data.notes)
    assert summary.item_count == 2, summary
    assert summary.open_count == 1, summary
    assert summary.done_count == 1, summary
    assert summary.step_count == 3, summary
    assert summary.note_count == 2, summary

    print("WORK CHECK PASSED")


if __name__ == "__main__":
    main()
