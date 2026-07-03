from __future__ import annotations

from typing import Any

from app.platform.constitution.runtime import get_runtime_constitution


def build_constitution_summary() -> dict[str, Any]:
    constitution = get_runtime_constitution()
    return {
        "company": constitution.company,
        "product": constitution.product,
        "milestone": constitution.milestone,
        "status": constitution.status,
        "loaded": constitution.loaded,
        "version": constitution.version,
        "source": constitution.source,
        "source_type": constitution.source_type,
        "hash": constitution.content_hash,
        "loaded_at": constitution.loaded_at,
        "rules": {
            "company_dna": constitution.company_dna,
            "operating_principles": constitution.operating_principles,
            "product_principles": constitution.product_principles,
            "engineering_rules": constitution.engineering_rules,
            "founder_rules": constitution.founder_rules,
            "approval_rules": constitution.approval_rules,
            "deployment_rules": constitution.deployment_rules,
            "security_rules": constitution.security_rules,
            "validation_rules": constitution.validation_rules,
        },
        "next_step": "All planning and workflow services should consume runtime_constitution rather than duplicating governance prompts.",
    }
