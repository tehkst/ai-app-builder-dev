from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.platform.knowledge_vault.models import KnowledgeEntry, KnowledgeVaultSummary


def build_knowledge_vault_summary() -> dict[str, Any]:
    entries = [
        KnowledgeEntry(
            "kv-001",
            "Company Constitution",
            "company-dna",
            "active",
            "Knowledge Curator",
            "Operating principles for product, engineering, and company behavior.",
            ["constitution", "principles", "governance"],
        ),
        KnowledgeEntry(
            "kv-002",
            "GCP Production Runbook",
            "runbook",
            "active",
            "Launch Engineer",
            "Deployment, verification, and production operation steps for Cloud Run.",
            ["gcp", "cloud-run", "deployment"],
        ),
        KnowledgeEntry(
            "kv-003",
            "Mission Control Architecture",
            "architecture",
            "active",
            "Engineering Lead",
            "Bounded context model for the autonomous software company operating system.",
            ["mission-control", "architecture", "bounded-context"],
        ),
        KnowledgeEntry(
            "kv-004",
            "Deployment Lessons Learned",
            "lesson",
            "active",
            "Launch Engineer",
            "Automated deployment should verify health, readiness, and Mission Control endpoints.",
            ["deployment", "verification", "learning"],
        ),
        KnowledgeEntry(
            "kv-005",
            "Customer Zero Policy",
            "operating-policy",
            "active",
            "Mission Control CEO",
            "AI Software Factory must use each capability internally before selling it externally.",
            ["dogfood", "customer-zero", "policy"],
        ),
    ]
    categories = sorted({entry.category for entry in entries})
    return asdict(
        KnowledgeVaultSummary(
            company="AI Software Factory",
            product="Knowledge Vault",
            purpose="Institutional memory for decisions, runbooks, lessons, and operating policy.",
            total_entries=len(entries),
            categories=categories,
            entries=entries,
        )
    )
