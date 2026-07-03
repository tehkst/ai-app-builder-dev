from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

CONSTITUTION_SOURCE = "company/knowledge/KV-0001.md"

FALLBACK_CONSTITUTION = """# KV-0001: Company Constitution

Operating principles for product, engineering, and company behavior.

## Company DNA
- AI Software Factory must run itself through Mission Control.
- Build company capabilities, not disconnected features.
- Customer Zero comes before external commercialization.

## Operating Principles
- Audit before implementing.
- Reuse existing functionality before creating new subsystems.
- Fix root causes instead of temporary patches.
- Protect production stability above all else.

## Engineering Rules
- Small, reviewable pull requests only.
- Feature branches only.
- No direct writes to main.
- Validation must pass before merge or deployment.
- Prefer maintainable templates/static JavaScript over giant inline HTML/JS.

## Founder Rules
- Founder approval is required before mutation, PR creation, merge, or production deployment.
- Roadmap approval authorizes planning only, not implementation.

## Security Rules
- No secret values in prompts or logs.
- Authentication, login, and session boundaries are protected unless explicitly scoped.
- Use least-privilege GitHub token or GitHub App.

## Deployment Rules
- GCP Cloud Run is the production platform.
- Railway is not part of the production architecture.
- Production traffic changes require explicit approval and rollback readiness.
"""


def load_constitution_text() -> dict[str, str]:
    path = Path(CONSTITUTION_SOURCE)
    if path.exists():
        return {"source": CONSTITUTION_SOURCE, "source_type": "knowledge-vault", "text": path.read_text(encoding="utf-8")}
    return {"source": CONSTITUTION_SOURCE, "source_type": "embedded-fallback", "text": FALLBACK_CONSTITUTION}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
