from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.platform.company_objects.models import CompanyObject, CompanyObjectRelationship


def build_company_object_registry() -> dict[str, Any]:
    objects = [
        CompanyObject(
            object_id="ADR-0001",
            object_type="adr",
            title="The Company Owns Its Knowledge",
            status="approved",
            owner="Chief Architect",
            summary="Institutional memory belongs to AI Software Factory, not any external AI model.",
            tags=["company-brain", "knowledge", "governance"],
        ),
        CompanyObject(
            object_id="SPEC-0001",
            object_type="policy",
            title="Company Brain Specification v1.0",
            status="approved",
            owner="CTO",
            summary="Blueprint for how the company thinks, remembers, decides, learns, and builds.",
            tags=["company-brain", "strategy"],
            relationships=[CompanyObjectRelationship("references", "ADR-0001", "Spec follows the company-owned knowledge principle.")],
        ),
        CompanyObject(
            object_id="BR-0001",
            object_type="resolution",
            title="Establish Company Brain Program",
            status="proposed",
            owner="Corporate Secretary",
            summary="Formalize Company Brain as the primary operating system of AI Software Factory.",
            tags=["board", "company-brain"],
            relationships=[CompanyObjectRelationship("created_from", "SPEC-0001", "Resolution implements the Company Brain specification.")],
        ),
        CompanyObject(
            object_id="M-0001",
            object_type="mission",
            title="Build Company Brain Foundation",
            status="active",
            owner="CTO",
            summary="Move company strategy and institutional memory from chat into AI Software Factory.",
            tags=["mission", "company-brain"],
            relationships=[CompanyObjectRelationship("implements", "BR-0001", "Mission executes the Company Brain resolution.")],
        ),
    ]
    return {
        "company": "AI Software Factory",
        "product": "Company Objects",
        "total_objects": len(objects),
        "objects": [asdict(item) for item in objects],
    }
