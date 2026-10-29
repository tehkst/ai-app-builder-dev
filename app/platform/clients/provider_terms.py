"""What each AI provider's terms say about the client code we send it, in plain words, so the
founder can tell the client before they agree. The consent dialog shows these facts and the start
request must name the version it showed (`terms_version`), so a stale page can't consent to facts
that have since changed. Each version is the date the terms were last read; re-read the sources and
bump `checked` when a provider changes its terms. This is a summary, not legal advice: the client
wording that goes with it is in docs/legal/AI_PROVIDER_TERMS_AND_CLIENT_CONSENT.md."""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

TERMS: Dict[str, Dict[str, Any]] = {
    "deepseek": {
        "company": "Hangzhou DeepSeek Artificial Intelligence Co., Ltd. (China)",
        "checked": "2026-10-29",
        "facts": [
            "Stored and processed in the People's Republic of China.",
            "May be used to train DeepSeek's models; its privacy policy offers an opt-out by email only.",
            "No fixed retention period: kept as long as the account exists.",
            "No zero-retention option.",
            "Contract governed by the laws of mainland China.",
        ],
        "sources": [
            "https://cdn.deepseek.com/policies/en-US/deepseek-open-platform-terms-of-service.html",
            "https://cdn.deepseek.com/policies/en-US/deepseek-privacy-policy.html",
        ],
    },
    "openai": {
        "company": "OpenAI (United States)",
        "checked": "2026-10-29",
        "facts": [
            "Not used to train OpenAI's models unless our account opts in to data sharing (off by default).",
            "Kept for up to 30 days for abuse monitoring, longer only if the law requires it.",
            "Processed in the United States unless a data-residency region is set up.",
            "Zero data retention only with OpenAI's approval for our account.",
        ],
        "sources": [
            "https://developers.openai.com/api/docs/guides/your-data",
            "https://openai.com/enterprise-privacy/",
        ],
    },
}

UNKNOWN_FACTS = ["We haven't summarised this provider's terms. Read them before sending client code."]


def terms_for(ai: Optional[Tuple[str, str]]) -> Optional[Dict[str, Any]]:
    """The facts to show for the provider a job would use now (None when no provider is set)."""
    if ai is None:
        return None
    known = TERMS.get(ai[0])
    if not known:
        return {"provider": ai[0], "company": ai[0], "facts": UNKNOWN_FACTS, "sources": [],
                "version": f"{ai[0]}-unreviewed"}
    return {"provider": ai[0], **known, "version": f"{ai[0]}-{known['checked']}"}


def check_version(ai: Optional[Tuple[str, str]], shown: Any) -> str:
    """The version the founder confirmed; refuses a confirmation of other (or no) facts."""
    terms = terms_for(ai)
    if terms is None or shown != terms["version"]:
        raise ValueError("The provider's terms shown to you are out of date. Reload and confirm again.")
    return terms["version"]
