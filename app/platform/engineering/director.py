from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from app.platform.engineering.scope_contract import ScopeContract, draft_scope_contract


@dataclass(frozen=True)
class EngineeringClassification:
    work_type: str
    division: str
    requested_capabilities: List[str]
    confidence: float
    reason: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "work_type": self.work_type,
            "division": self.division,
            "requested_capabilities": self.requested_capabilities,
            "confidence": self.confidence,
            "reason": self.reason,
        }


def classify_engineering_request(request_text: str) -> EngineeringClassification:
    normalized = " ".join((request_text or "").lower().split())

    if _contains_any(normalized, ["migration", "migrate", "schema", "database migration", "alembic"]):
        return EngineeringClassification(
            work_type="migration",
            division="platform",
            requested_capabilities=["platform.migration", "platform.testing", "platform.rollback"],
            confidence=0.86,
            reason="Request refers to database or schema migration work.",
        )

    if _contains_any(normalized, ["bug", "fix", "error", "failed", "failure", "broken", "regression"]):
        return EngineeringClassification(
            work_type="bug_fix",
            division="platform",
            requested_capabilities=["platform.repair", "platform.testing", "platform.review"],
            confidence=0.82,
            reason="Request describes a defect, failure, or repair action.",
        )

    if _contains_any(normalized, ["security", "permission", "auth", "secret", "vulnerability", "risk"]):
        return EngineeringClassification(
            work_type="security",
            division="platform",
            requested_capabilities=["platform.security", "platform.review", "platform.testing"],
            confidence=0.82,
            reason="Request is security-sensitive or permission-related.",
        )

    if _contains_any(normalized, ["validator", "checker", "contract", "workflow", "registry", "agent", "self", "factory", "platform", "internal"]):
        return EngineeringClassification(
            work_type="platform_improvement",
            division="platform",
            requested_capabilities=["platform.scope", "platform.builder", "platform.validator", "platform.testing"],
            confidence=0.88,
            reason="Request targets internal factory capability or platform workflow behavior.",
        )

    if _contains_any(normalized, ["documentation", "docs", "readme", "guide", "handover"]):
        return EngineeringClassification(
            work_type="documentation",
            division="platform",
            requested_capabilities=["platform.documentation", "platform.review"],
            confidence=0.80,
            reason="Request targets documentation or operating procedures.",
        )

    if _contains_any(normalized, ["build app", "crm", "dashboard", "user", "customer", "frontend", "react", "fastapi app"]):
        return EngineeringClassification(
            work_type="customer_product",
            division="product",
            requested_capabilities=["customer.backend", "customer.frontend", "customer.testing"],
            confidence=0.78,
            reason="Request appears to describe a customer-facing product or application.",
        )

    return EngineeringClassification(
        work_type="research",
        division="platform",
        requested_capabilities=["platform.research", "platform.scope"],
        confidence=0.50,
        reason="Request did not clearly map to a build, fix, migration, security, documentation, or product task.",
    )


def draft_scope_from_request(request_text: str) -> ScopeContract:
    classification = classify_engineering_request(request_text)
    goal = " ".join((request_text or "").strip().split())
    if not goal:
        goal = "No goal provided"

    return draft_scope_contract(
        goal=goal,
        work_type=classification.work_type,
        requested_capabilities=classification.requested_capabilities,
        acceptance_criteria=[
            "Scope contract is valid before build begins.",
            "Generated or changed artifacts match the approved scope.",
            "Review and test gates pass before materialization approval.",
        ],
        test_plan=[
            "Validate scope contract fields and required approvals.",
            "Run platform validation checks relevant to the requested capabilities.",
            "Confirm no generated artifact is materialized before approval.",
        ],
        in_scope=[classification.reason],
        out_of_scope=[
            "Filesystem materialization before approval.",
            "External deployment before rollout approval.",
            "Unscoped change requests.",
        ],
        affected_systems=_affected_systems_for_classification(classification),
        risks=_risks_for_classification(classification),
    )


def _contains_any(value: str, needles: List[str]) -> bool:
    return any(needle in value for needle in needles)


def _affected_systems_for_classification(classification: EngineeringClassification) -> List[str]:
    if classification.division == "product":
        return ["generated_artifacts", "product_preview", "approval_gate"]
    return ["platform_workflow", "agent_registry", "validation_pipeline", "approval_gate"]


def _risks_for_classification(classification: EngineeringClassification) -> List[str]:
    risks = ["scope_drift", "incomplete_tests", "premature_materialization"]
    if classification.work_type == "migration":
        risks.append("database_rollback_required")
    if classification.work_type == "security":
        risks.append("permission_boundary_regression")
    return risks
