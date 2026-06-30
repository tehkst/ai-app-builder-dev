from __future__ import annotations

from typing import Any

from app.platform.company_objects.service import build_company_object_registry


def build_company_graph() -> dict[str, Any]:
    registry = build_company_object_registry()
    objects = registry["objects"]

    nodes = [
        {
            "id": item["object_id"],
            "type": item["object_type"],
            "title": item["title"],
            "status": item["status"],
            "owner": item["owner"],
        }
        for item in objects
    ]

    edges: list[dict[str, str]] = []
    for item in objects:
        for relationship in item.get("relationships", []):
            edges.append(
                {
                    "source": item["object_id"],
                    "relationship_type": relationship.get("relationship_type", ""),
                    "target": relationship.get("target_object_id", ""),
                    "description": relationship.get("description", ""),
                }
            )

    return {
        "company": "AI Software Factory",
        "product": "Company Graph",
        "source": "company/objects",
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "nodes": nodes,
        "edges": edges,
    }
