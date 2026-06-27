from __future__ import annotations

from typing import Dict, Optional

from app.platform.pmo.planning_models import WorkflowItem


WORKFLOWS: Dict[str, WorkflowItem] = {
    "constitution_foundation_workflow": WorkflowItem(
        workflow_id="constitution_foundation_workflow",
        story_id="define_constitution_rules",
        name="Constitution Foundation Workflow",
        task_ids=["implement_constitution_registry", "implement_constitution_check"],
        status="ready",
    ),
}


def all_workflows() -> Dict[str, WorkflowItem]:
    return dict(WORKFLOWS)


def get_workflow(workflow_id: str) -> Optional[WorkflowItem]:
    return WORKFLOWS.get(workflow_id)
