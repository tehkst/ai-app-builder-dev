from __future__ import annotations

from typing import Dict, List

from app.platform.agents.manifest_registry import all_manifests
from app.platform.knowledge.models import KnowledgeEdge, KnowledgeNode
from app.platform.memory.registry import all_memory_scopes
from app.platform.organization.registry import all_departments, all_teams, get_organization
from app.platform.projects.registry import all_projects


def build_knowledge_nodes() -> Dict[str, KnowledgeNode]:
    organization = get_organization()
    nodes: Dict[str, KnowledgeNode] = {
        organization.organization_id: KnowledgeNode(
            node_id=organization.organization_id,
            node_type="organization",
            name=organization.name,
            metadata={},
        )
    }

    for department in all_departments().values():
        nodes[department.department_id] = KnowledgeNode(
            node_id=department.department_id,
            node_type="department",
            name=department.name,
            metadata={"lead_agent_id": department.lead_agent_id},
        )

    for team in all_teams().values():
        nodes[team.team_id] = KnowledgeNode(
            node_id=team.team_id,
            node_type="team",
            name=team.name,
            metadata={"department_id": team.department_id, "lead_agent_id": team.lead_agent_id},
        )

    for agent_id, manifest in all_manifests().items():
        nodes[agent_id] = KnowledgeNode(
            node_id=agent_id,
            node_type="agent",
            name=agent_id,
            metadata={"department": manifest.department},
        )

    for scope in all_memory_scopes().values():
        nodes[scope.scope_id] = KnowledgeNode(
            node_id=scope.scope_id,
            node_type="memory_scope",
            name=scope.scope_id,
            metadata={"owner_type": scope.owner_type, "owner_id": scope.owner_id},
        )

    for project in all_projects().values():
        nodes[project.project_id] = KnowledgeNode(
            node_id=project.project_id,
            node_type="project",
            name=project.name,
            metadata={"owning_department_id": project.owning_department_id},
        )

    return nodes


def build_knowledge_edges() -> List[KnowledgeEdge]:
    organization = get_organization()
    edges: List[KnowledgeEdge] = []

    for department_id in organization.department_ids:
        edges.append(KnowledgeEdge(
            edge_id=f"{organization.organization_id}_contains_{department_id}",
            source_node_id=organization.organization_id,
            relationship="contains",
            target_node_id=department_id,
            metadata={},
        ))

    for department in all_departments().values():
        edges.append(KnowledgeEdge(
            edge_id=f"{department.department_id}_uses_memory_{department.memory_scope}",
            source_node_id=department.department_id,
            relationship="uses_memory",
            target_node_id=department.memory_scope,
            metadata={},
        ))
        for team_id in department.team_ids:
            edges.append(KnowledgeEdge(
                edge_id=f"{department.department_id}_contains_{team_id}",
                source_node_id=department.department_id,
                relationship="contains",
                target_node_id=team_id,
                metadata={},
            ))

    for team in all_teams().values():
        edges.append(KnowledgeEdge(
            edge_id=f"{team.team_id}_uses_memory_{team.memory_scope}",
            source_node_id=team.team_id,
            relationship="uses_memory",
            target_node_id=team.memory_scope,
            metadata={},
        ))
        for agent_id in team.member_agent_ids:
            edges.append(KnowledgeEdge(
                edge_id=f"{team.team_id}_contains_{agent_id}",
                source_node_id=team.team_id,
                relationship="contains",
                target_node_id=agent_id,
                metadata={},
            ))

    for agent_id, manifest in all_manifests().items():
        for artifact_path in manifest.owns_artifacts:
            artifact_id = "artifact:" + artifact_path
            edges.append(KnowledgeEdge(
                edge_id=f"{agent_id}_owns_{artifact_id}",
                source_node_id=agent_id,
                relationship="owns",
                target_node_id=artifact_id,
                metadata={"path": artifact_path},
            ))

    for project in all_projects().values():
        edges.append(KnowledgeEdge(
            edge_id=f"{project.owning_department_id}_owns_{project.project_id}",
            source_node_id=project.owning_department_id,
            relationship="owns",
            target_node_id=project.project_id,
            metadata={},
        ))
        for team_id in project.team_ids:
            edges.append(KnowledgeEdge(
                edge_id=f"{project.project_id}_uses_{team_id}",
                source_node_id=project.project_id,
                relationship="contains",
                target_node_id=team_id,
                metadata={},
            ))

    return edges
