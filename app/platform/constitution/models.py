from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, List


@dataclass(frozen=True)
class ConstitutionRule:
    rule_id: str
    title: str
    category: str
    severity: str
    description: str
    applies_to: List[str]
    blocks_release: bool


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    blocked_by: List[str]
    warnings: List[str]


@dataclass(frozen=True)
class RuntimeConstitution:
    company: str
    product: str
    milestone: str
    status: str
    version: str
    source: str
    source_type: str
    content_hash: str
    loaded: bool
    loaded_at: str
    company_dna: list[str] = field(default_factory=list)
    operating_principles: list[str] = field(default_factory=list)
    product_principles: list[str] = field(default_factory=list)
    engineering_rules: list[str] = field(default_factory=list)
    founder_rules: list[str] = field(default_factory=list)
    approval_rules: list[str] = field(default_factory=list)
    deployment_rules: list[str] = field(default_factory=list)
    security_rules: list[str] = field(default_factory=list)
    validation_rules: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def compact(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "source": self.source,
            "source_type": self.source_type,
            "hash": self.content_hash,
            "loaded": self.loaded,
            "status": self.status,
            "company_dna": self.company_dna,
            "operating_principles": self.operating_principles,
            "engineering_rules": self.engineering_rules,
            "founder_rules": self.founder_rules,
            "approval_rules": self.approval_rules,
            "deployment_rules": self.deployment_rules,
            "security_rules": self.security_rules,
            "validation_rules": self.validation_rules,
        }
