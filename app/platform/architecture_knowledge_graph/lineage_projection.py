from __future__ import annotations

from typing import Any, Dict

from app.platform.delivery_lineage.service import build_latest_lineage_summary


def project_delivery_lineage() -> Dict[str, Any]:
    summary = build_latest_lineage_summary()
    if summary.get("status") != "ready":
        return {"nodes": [], "edges": []}
    mission_id = str(summary["mission_id"])
    workflow_run_id = str(summary["workflow_run_id"])
    mission_node = "mission:%s" % mission_id
    workflow_node = "workflow:%s" % workflow_run_id
    evidence = {
        "kind": "delivery-lineage",
        "source": "autonomous-delivery-lineage-v1",
        "entry_count": summary["entry_count"],
        "completeness": summary["evidence_completeness"],
    }
    nodes = [
        {
            "id": mission_node, "type": "Mission", "name": mission_id,
            "authority": "PlatformWorkflowRun", "lifecycle": "Active",
            "purpose": "Canonical governed software-delivery mission.",
            "evidence": [evidence],
        },
        {
            "id": workflow_node, "type": "Workflow", "name": workflow_run_id,
            "authority": "PlatformWorkflowRun", "lifecycle": "Active",
            "purpose": "Durable execution workflow for the mission.",
            "evidence": [evidence],
        },
    ]
    return {
        "nodes": nodes,
        "edges": [{
            "source": mission_node, "target": workflow_node, "type": "contains",
            "evidence": "autonomous-delivery-lineage-v1",
        }],
    }
