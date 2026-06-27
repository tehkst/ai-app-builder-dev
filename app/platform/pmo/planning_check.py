from __future__ import annotations

from app.platform.pmo.epic_registry import all_epics
from app.platform.pmo.feature_registry import all_features
from app.platform.pmo.planning_engine import highest_priority_ready_story, tasks_for_next_story, workflow_for_story
from app.platform.pmo.program_registry import get_program
from app.platform.pmo.story_registry import all_stories
from app.platform.pmo.task_registry import all_tasks
from app.platform.pmo.workflow_registry import all_workflows


def main() -> None:
    epics = all_epics()
    features = all_features()
    stories = all_stories()
    tasks = all_tasks()
    workflows = all_workflows()

    assert epics, "epics are required"
    assert features, "features are required"
    assert stories, "stories are required"
    assert tasks, "tasks are required"
    assert workflows, "workflows are required"

    for epic in epics.values():
        assert get_program(epic.program_id) is not None, epic
        assert epic.status in {"planned", "ready", "in_progress", "completed", "blocked"}, epic

    for feature in features.values():
        assert feature.epic_id in epics, feature

    for story in stories.values():
        assert story.feature_id in features, story
        for dependency in story.depends_on:
            assert dependency in stories, {"story": story.story_id, "missing_dependency": dependency}

    for task in tasks.values():
        assert task.story_id in stories, task
        assert task.owner_agent, task
        assert task.required_capability, task

    for workflow in workflows.values():
        assert workflow.story_id in stories, workflow
        for task_id in workflow.task_ids:
            assert task_id in tasks, {"workflow": workflow.workflow_id, "missing_task": task_id}

    story = highest_priority_ready_story()
    assert story is not None, "a ready story is required"
    assert story.story_id == "define_constitution_rules", story

    next_tasks = tasks_for_next_story()
    assert len(next_tasks) == 2, next_tasks

    workflow = workflow_for_story(story.story_id)
    assert workflow is not None, story
    assert workflow.workflow_id == "constitution_foundation_workflow", workflow

    print("PMO PLANNING CHECK PASSED")


if __name__ == "__main__":
    main()
