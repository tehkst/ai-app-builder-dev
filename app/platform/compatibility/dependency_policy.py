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
    "langchain": {
        "purpose": "LLM orchestration support.",
        "risk_level": "high",
        "notes": "Prompt, tool, and memory flows must be reviewed for injection and data leakage risks.",
    },
    "langgraph": {
        "purpose": "AI factory workflow orchestration.",
        "risk_level": "high",
        "notes": "Graph state must not allow generated customer code to mutate platform code.",
    },
    "langsmith": {
        "purpose": "Observability and tracing.",
        "risk_level": "high",
        "notes": "Trace metadata must avoid secrets and sensitive customer data.",
    },
}


CANDIDATE_PLATFORM_DEPENDENCIES = {
    "slowapi": {
        "purpose": "Rate limiting for FastAPI routes.",
        "risk_level": "medium",
        "approval_status": "candidate",
        "notes": "Candidate for /platform/* and /api/auth/* abuse protection. Must be pinned and validated before production use.",
    },
}


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
