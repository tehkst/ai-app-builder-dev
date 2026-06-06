from __future__ import annotations

from typing import Any, Dict, List


NOISE_HINTS = [
    "i saw",
    "my friend said",
    "maybe",
    "not sure",
    "random",
    "bangkok",
    "nice color",
]

RISK_HINTS = [
    "payment",
    "payments",
    "stripe",
    "credit card",
    "bank",
    "delete user",
    "production",
    "deploy",
    "personal data",
    "medical",
    "insurance",
]

CONFLICT_PAIRS = [
    ("crm", "whatsapp"),
    ("simple", "like salesforce"),
    ("no login", "user login"),
    ("no database", "store data"),
]


def _contains(text: str, keyword: str) -> bool:
    return keyword.lower() in text.lower()


def _sentence_split(text: str) -> List[str]:
    cleaned = text.replace("\n", ". ")
    parts = [part.strip(" .,-") for part in cleaned.split(".")]
    return [part for part in parts if part]


def clean_requirements(raw_goal: str) -> Dict[str, Any]:
    text = raw_goal.strip()
    lower = text.lower()
    parts = _sentence_split(text)

    core_requirements: List[str] = []
    optional_requirements: List[str] = []
    unclear_requirements: List[str] = []
    noise: List[str] = []
    risk_flags: List[str] = []
    conflicts: List[Dict[str, str]] = []

    if "school transport" in lower:
        core_requirements.append("Build a school transport application")
    elif "transport app" in lower or "logistics app" in lower:
        core_requirements.append("Build a transport/logistics application")
    elif "expense" in lower:
        core_requirements.append("Build an expense tracking application")
    elif "booking" in lower:
        core_requirements.append("Build a booking application")
    elif "crm" in lower:
        core_requirements.append("Build a CRM application")
    elif "dashboard app" in lower:
        core_requirements.append("Build a dashboard application")

    if "route" in lower or "routes" in lower:
        core_requirements.append("Manage routes")
    if "driver" in lower or "drivers" in lower:
        core_requirements.append("Manage drivers")
    if "vehicle" in lower or "vehicles" in lower:
        core_requirements.append("Manage vehicles")
    if "parent" in lower or "parents" in lower:
        core_requirements.append("Parent-facing features")
    if "notification" in lower or "notifications" in lower:
        core_requirements.append("Notifications")
    if "report" in lower or "reports" in lower:
        core_requirements.append("Reports")
    if "budget" in lower or "budgets" in lower:
        core_requirements.append("Manage budgets")
    if "categor" in lower:
        core_requirements.append("Manage categories")

    if "contact" in lower or "contacts" in lower:
        core_requirements.append("Manage contacts")
    if "compan" in lower:
        core_requirements.append("Manage companies")
    if "deal" in lower:
        core_requirements.append("Manage deals")
    if "note" in lower or "notes" in lower:
        core_requirements.append("Manage notes")
    if "login" in lower or "user" in lower:
        core_requirements.append("User login and authentication")

    if "ai" in lower:
        optional_requirements.append("AI assistant or AI-powered helper")
    if "dashboard" in lower and "Dashboard" not in core_requirements and "Build a dashboard application" not in core_requirements:
        optional_requirements.append("Dashboard")
    if "payment" in lower or "payments" in lower or "stripe" in lower:
        optional_requirements.append("Payment integration")

    for part in parts:
        part_lower = part.lower()

        if any(hint in part_lower for hint in NOISE_HINTS):
            noise.append(part)

        if "maybe" in part_lower or "not sure" in part_lower or "or maybe" in part_lower:
            unclear_requirements.append(part)

    for hint in RISK_HINTS:
        if hint in lower:
            risk_flags.append(hint)

    for left, right in CONFLICT_PAIRS:
        if left in lower and right in lower:
            conflicts.append(
                {
                    "left": left,
                    "right": right,
                    "reason": f"Requirement mentions both '{left}' and '{right}', which may need clarification.",
                }
            )

    if not core_requirements:
        architecture_fit = "unclear"
        unclear_requirements.append("No clear core application type detected")
    elif conflicts:
        architecture_fit = "partially_fits"
    else:
        architecture_fit = "fits"

    return {
        "raw_goal": raw_goal,
        "architecture_fit": architecture_fit,
        "core_requirements": core_requirements,
        "optional_requirements": optional_requirements,
        "unclear_requirements": unclear_requirements,
        "conflicts": conflicts,
        "noise": noise,
        "risk_flags": risk_flags,
        "approval_recommended": bool(risk_flags or conflicts),
    }


def build_clean_goal(requirements: Dict[str, Any]) -> str:
    core = requirements.get("core_requirements") or []
    optional = requirements.get("optional_requirements") or []

    if not core:
        return requirements.get("raw_goal", "")

    clean_goal = "; ".join(core)

    if optional:
        clean_goal += "; Optional: " + "; ".join(optional)

    return clean_goal
