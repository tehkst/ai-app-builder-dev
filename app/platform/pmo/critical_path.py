from __future__ import annotations

from typing import List

from app.platform.pmo.dependency_graph import story_dependency_graph


def longest_dependency_chain(story_id: str) -> List[str]:
    graph = story_dependency_graph()

    def chain(current: str) -> List[str]:
        dependencies = graph.get(current, [])
        if not dependencies:
            return [current]
        chains = [chain(dependency) for dependency in dependencies]
        longest = max(chains, key=len)
        return longest + [current]

    return chain(story_id)


def critical_path() -> List[str]:
    graph = story_dependency_graph()
    if not graph:
        return []
    return max((longest_dependency_chain(story_id) for story_id in graph), key=len)
