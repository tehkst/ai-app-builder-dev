from __future__ import annotations

from app.platform.work.work_models import WorkContext
from app.platform.work.work_store import make_item, make_note, make_step


def run_demo_work() -> WorkContext:
    items = [
        make_item("work1", "tenant_platform", "Prepare CRM app", "project", "user_platform_owner"),
        make_item("work2", "tenant_platform", "Review deployment", "review", "user_platform_owner", "done"),
    ]
    steps = [
        make_step("step1", "work1", "Confirm brief", 1, "done"),
        make_step("step2", "work1", "Generate app", 2, "active"),
        make_step("step3", "work1", "Review app", 3, "new"),
    ]
    notes = [
        make_note("note1", "work1", "user_platform_owner", "Use the CRM starter item."),
        make_note("note2", "work2", "user_platform_owner", "Deployment review completed."),
    ]
    return WorkContext(
        items=items,
        steps=steps,
        notes=notes,
        metadata={"flow": "work"},
    )
