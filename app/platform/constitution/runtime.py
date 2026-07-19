from __future__ import annotations

import hashlib
import re
from functools import lru_cache

from app.platform.constitution.loader import load_constitution_text, utc_now
from app.platform.constitution.models import RuntimeConstitution
from app.platform.constitution.rules import all_rules

RULE_FALLBACKS = {
    "company_dna": [
        "AI Software Factory must run itself through Mission Control.",
        "Build company capabilities, not disconnected features.",
        "Customer Zero comes before external commercialization.",
    ],
    "operating_principles": [
        "Audit before implementing.",
        "Reuse existing functionality before creating new subsystems.",
        "Fix root causes instead of temporary patches.",
        "Protect production stability above all else.",
        "Capability and Authority are separate concepts. Any AI component may possess execution capability. Execution authority is determined exclusively by the Governance Authorization Layer. No component may bypass governance.",
    ],
    "product_principles": [
        "Mission Control is the primary operating interface.",
        "Founder experience must stay clear, reviewable, and approval-gated.",
    ],
    "engineering_rules": [
        "Small, reviewable pull requests only.",
        "Feature branches only.",
        "No direct writes to main.",
        "Validation must pass before merge or deployment.",
        "Prefer maintainable templates/static JavaScript over giant inline HTML/JS.",
    ],
    "founder_rules": [
        "Founder approval is required before mutation, PR creation, merge, or production deployment.",
        "Roadmap approval authorizes planning only, not implementation.",
    ],
    "approval_rules": [
        "No mission execution begins without explicit founder approval.",
        "Deployment requires explicit founder review.",
    ],
    "deployment_rules": [
        "GCP Cloud Run is the production platform.",
        "Railway is not part of the production architecture.",
        "Production traffic changes require explicit approval and rollback readiness.",
    ],
    "security_rules": [
        "No secret values in prompts or logs.",
        "Authentication, login, and session boundaries are protected unless explicitly scoped.",
        "Use least-privilege GitHub token or GitHub App.",
    ],
    "validation_rules": [
        "Run platform validation before merge.",
        "CI validation must pass before deployment.",
    ],
}

SECTION_MAP = {
    "company dna": "company_dna",
    "operating principles": "operating_principles",
    "product principles": "product_principles",
    "engineering rules": "engineering_rules",
    "founder rules": "founder_rules",
    "approval rules": "approval_rules",
    "deployment rules": "deployment_rules",
    "security rules": "security_rules",
    "validation rules": "validation_rules",
}


@lru_cache(maxsize=1)
def get_runtime_constitution() -> RuntimeConstitution:
    loaded = load_constitution_text()
    text = loaded["text"]
    extracted = _extract_sections(text)
    rules = all_rules()
    engineering_rules = _merge(extracted.get("engineering_rules"), RULE_FALLBACKS["engineering_rules"])
    for rule_id, rule in rules.items():
        engineering_rules.append(f"{rule_id}: {rule.get('category')} rule applies to {', '.join(rule.get('targets', []))}.")
    return RuntimeConstitution(
        company="AI Software Factory",
        product="Constitution Runtime",
        milestone="MC-001",
        status="constitution-runtime-loaded",
        version="KV-0001",
        source=loaded["source"],
        source_type=loaded["source_type"],
        content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
        loaded=True,
        loaded_at=utc_now(),
        company_dna=_merge(extracted.get("company_dna"), RULE_FALLBACKS["company_dna"]),
        operating_principles=_merge(extracted.get("operating_principles"), RULE_FALLBACKS["operating_principles"]),
        product_principles=_merge(extracted.get("product_principles"), RULE_FALLBACKS["product_principles"]),
        engineering_rules=_dedupe(engineering_rules),
        founder_rules=_merge(extracted.get("founder_rules"), RULE_FALLBACKS["founder_rules"]),
        approval_rules=_merge(extracted.get("approval_rules"), RULE_FALLBACKS["approval_rules"]),
        deployment_rules=_merge(extracted.get("deployment_rules"), RULE_FALLBACKS["deployment_rules"]),
        security_rules=_merge(extracted.get("security_rules"), RULE_FALLBACKS["security_rules"]),
        validation_rules=_merge(extracted.get("validation_rules"), RULE_FALLBACKS["validation_rules"]),
    )


def build_constitution_context() -> dict[str, object]:
    constitution = get_runtime_constitution()
    return constitution.compact()


def _extract_sections(text: str) -> dict[str, list[str]]:
    current: str | None = None
    sections: dict[str, list[str]] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        heading = re.sub(r"^#+\s*", "", line).strip().lower()
        if heading in SECTION_MAP:
            current = SECTION_MAP[heading]
            sections.setdefault(current, [])
            continue
        if current and line.startswith("-"):
            sections.setdefault(current, []).append(line.lstrip("- ").strip())
    return sections


def _merge(primary: list[str] | None, fallback: list[str]) -> list[str]:
    return _dedupe((primary or []) + fallback)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        clean = " ".join(str(item).split())
        key = clean.lower()
        if clean and key not in seen:
            seen.add(key)
            result.append(clean)
    return result
