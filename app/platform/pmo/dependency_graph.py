from __future__ import annotations

from typing import Dict, List, Set

from app.platform.pmo.story_registry import all_stories


def story_dependency_graph() -> Dict[str, List[str]]:
    return {
        story.story_id: list(story.depends_on)
        for story in all_stories().values()
    }


def reverse_dependency_graph() -> Dict[str, List[str]]:
    reverse: Dict[str, List[str]] = {story_id: [] for story_id in story_dependency_graph()}
    for story_id, dependencies in story_dependency_graph().items():
        for dependency in dependencies:
            reverse.setdefault(dependency, []).append(story_id)
    return reverse


def transitive_dependencies(story_id: str) -> Set[str]:
    graph = story_dependency_graph()
    visited: Set[str] = set()

    def visit(current: str) -> None:
        for dependency in graph.get(current, []):
            if dependency in visited:
                continue
            visited.add(dependency)
            visit(dependency)

    visit(story_id)
    return visited
