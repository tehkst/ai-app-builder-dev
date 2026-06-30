from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.platform.board_room.service import build_board_room_summary
from app.platform.company_brain.repository import FileCompanyBrainRepository
from app.platform.company_graph.service import build_company_graph
from app.platform.company_objects.service import build_company_object_registry
from app.platform.knowledge_vault.service import build_knowledge_vault_summary


def build_company_brain_repository_summary() -> dict[str, Any]:
    repository = FileCompanyBrainRepository()
    artifacts = repository.list_artifacts()
    company_objects = build_company_object_registry()
    knowledge_vault = build_knowledge_vault_summary()
    board_room = build_board_room_summary()
    company_graph = build_company_graph()
    return {
        "company": "AI Software Factory",
        "product": "Company Brain Repository",
        "storage": "repository-filesystem",
        "status": "integrated",
        "total_artifacts": len(artifacts),
        "domains": {
            "company_objects": {
                "total_objects": company_objects["total_objects"],
                "storage": company_objects.get("storage", "repository-filesystem"),
            },
            "knowledge_vault": {
                "total_entries": knowledge_vault["total_entries"],
                "storage": knowledge_vault.get("storage", "repository-filesystem"),
            },
            "board_room": {
                "meeting_id": board_room["meeting"]["meeting_id"],
                "decisions": len(board_room["meeting"].get("decisions", [])),
            },
            "company_graph": {
                "total_nodes": company_graph["total_nodes"],
                "total_edges": company_graph["total_edges"],
            },
        },
        "artifacts": [
            {
                "path": artifact.path,
                "title": artifact.title,
                "artifact_type": artifact.artifact_type,
            }
            for artifact in artifacts
        ],
    }


def get_company_brain_artifact(path: str) -> dict[str, Any]:
    repository = FileCompanyBrainRepository()
    artifact = repository.get_artifact(path)
    return asdict(artifact)
