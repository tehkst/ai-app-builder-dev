"""Approved dependency policy for the AI Software Factory platform.

This module documents platform dependency intent, allowed usage, and risk notes.
It is intentionally conservative because this is a cybersecurity-first AI SaaS.
Generated customer application dependencies are governed separately by template and
manifest guards.
"""

APPROVED_PLATFORM_DEPENDENCIES = {
    "fastapi": {
        "purpose": "Platform API framework.",
        "risk_level": "medium",
        "notes": "All platform routes must use authentication, bounded responses, and safe response shaping.",
    },
    "sqlalchemy": {
        "purpose": "Platform persistence ORM.",
        "risk_level": "medium",
        "notes": "Use parameterized ORM queries only. Do not build SQL with string interpolation.",
    },
    "python-dotenv": {
        "purpose": "Local development environment loading.",
        "risk_level": "low",
        "notes": "Production secrets must come from managed secret storage, not committed files.",
    },
    "openai": {
        "purpose": "LLM provider SDK.",
        "risk_level": "high",
        "notes": "Never log API keys, raw secrets, or customer-sensitive prompts in plaintext.",
    },
    "pyyaml": {
        "purpose": "YAML parsing for the Orca workforce manifest and Nautilus recipes.",
        "risk_level": "medium",
        "notes": "Always yaml.safe_load; never yaml.load on untrusted input.",
    },
    "reportlab": {
        "purpose": "PDF reports (Codebase Health Check).",
        "risk_level": "low",
        "notes": "Escape every client-derived string before it enters a Paragraph (it parses markup).",
    },
    "slowapi": {
        "purpose": "Rate limiting for FastAPI routes.",
        "risk_level": "medium",
        "notes": "Approved for /platform/* and /api/auth/* abuse protection. Must be pinned and validated before production use.",
    },
}


CANDIDATE_PLATFORM_DEPENDENCIES = {}


REJECTED_PLATFORM_DEPENDENCIES = {
    "unmaintained_security_middleware": {
        "reason": "Placeholder category for abandoned or low-trust security packages.",
    },
}


DEPENDENCY_POLICY_RULES = [
    "Do not add new platform dependencies without adding them to this policy.",
    "Do not expose raw metadata_json or secrets through APIs.",
    "Do not log tokens, API keys, passwords, generated secrets, or customer-sensitive prompts.",
    "Prefer standard library or already-approved dependencies when practical.",
    "Pin production dependency versions before deployment.",
    "Run compatibility scan and graph test after dependency changes.",
]
