from __future__ import annotations

from typing import Any, Dict

def build_workforce_summary() -> Dict[str, Any]:
    """Compatibility adapter over the canonical Organisation projection."""
    from app.platform.executive_intelligence.service import build_executive_intelligence_briefing
    from app.platform.organization_console.service import _departments, _workers

    workers = _workers()
    departments = _departments(workers)
    executive_state = build_executive_intelligence_briefing()
    return {
        "organization_name": "AI Software Factory",
        "workforce_name": "AI Organisation",
        "description": "Compatibility view over the canonical Organisation Console projection.",
        "total_employees": len(workers),
        "active_employees": sum(item["lifecycle_status"] == "active" for item in workers),
        "departments": [item["name"] for item in departments],
        "employees": [
            {
                "employee_id": item["agent_id"],
                "name": item["display_name"],
                "role": item["role_title"],
                "department": item["department_id"],
                "manager": item.get("reports_to"),
                "mission": item["description"],
                "status": item["runtime_status"],
                "skills": item["capabilities"],
                "kpis": [],
            }
            for item in workers
        ],
        "authority": "organisation-console-v1",
        "deprecated_route": True,
        "canonical_route": "/mission-control/organisation/query",
        "synthetic_workers": False,
        "executive_state_contract": executive_state.get("state_contract_version"),
    }
