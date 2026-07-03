from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

MODE_DEFINITIONS = {
    "architecture_review": {"label": "Architecture Review", "owner": "AI CTO", "departments": ["Engineering Command", "Product", "Knowledge Vault"], "workflow_type": "roadmap"},
    "engineering_roadmap": {"label": "Engineering Roadmap", "owner": "Engineering Manager", "departments": ["Engineering Command", "QA", "DevOps"], "workflow_type": "roadmap"},
    "implementation": {"label": "Implementation Mission", "owner": "Engineering Manager", "departments": ["Engineering Command", "QA"], "workflow_type": "implementation"},
    "bug_fix": {"label": "Bug Fix", "owner": "Engineering Manager", "departments": ["Engineering Command", "QA"], "workflow_type": "implementation"},
    "deployment": {"label": "Deployment", "owner": "DevOps Lead", "departments": ["Launch Center", "QA"], "workflow_type": "deployment"},
    "security_auth": {"label": "Authentication / Security", "owner": "Security Advisor", "departments": ["Security", "Engineering Command"], "workflow_type": "security_review"},
    "strategy": {"label": "Strategy", "owner": "AI CEO", "departments": ["Executive Office", "Product"], "workflow_type": "strategy"},
    "product": {"label": "Product Planning", "owner": "Product Manager", "departments": ["Product", "Engineering Command"], "workflow_type": "roadmap"},
    "research": {"label": "Research", "owner": "Product Manager", "departments": ["Product", "Executive Office"], "workflow_type": "research"},
    "knowledge": {"label": "Knowledge / Clarification", "owner": "Knowledge Curator", "departments": ["Knowledge Vault"], "workflow_type": "knowledge_note"},
    "general": {"label": "General Conversation", "owner": "Founder", "departments": ["Executive Office"], "workflow_type": "working_note"},
}

ROADMAP_TRIGGERS = ["roadmap", "prioritized", "next 10", "engineering missions", "architectural review", "architecture review", "live architectural review", "do not implement", "only produce", "executive engineering roadmap"]
IMPLEMENTATION_TRIGGERS = ["implement", "build", "fix", "code", "create pr", "open pr", "pull request", "execute", "small reviewable pr"]
DEPLOYMENT_TRIGGERS = ["deploy", "deployment", "cloud run", "rollback", "release", "traffic", "revision"]
ARCHITECTURE_TRIGGERS = ["architecture", "architectural", "duplicate", "root cause", "technical debt", "refactor", "bounded context"]
AUTH_TRIGGERS = ["auth", "authentication", "login", "session", "token", "credential"]
STRATEGY_TRIGGERS = ["strategy", "fundraising", "pricing", "market", "positioning", "business model"]
PRODUCT_TRIGGERS = ["founder experience", "product", "ux", "workflow", "dashboard", "mission control"]
RESEARCH_TRIGGERS = ["research", "investigate", "compare", "benchmark", "explore"]
KNOWLEDGE_TRIGGERS = ["explain", "clarify", "why", "what is", "how does", "what does"]
UI_PANEL_MARKERS = ["conversation intelligence", "mode", "decisions", "actions", "knowledge", "mission suggested", "workflow generated", "create proposal"]


def build_conversation_intelligence_summary() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "AI Conversation Intelligence Engine",
        "milestone": "CI-03",
        "status": "executive-semantic-intelligence-ready",
        "purpose": "Normalize founder intent into structured executive semantics before workflow, proposal, or governance processing.",
        "modes": [definition["label"] for definition in MODE_DEFINITIONS.values()],
        "endpoint": "POST /mission-control/conversation-intelligence/analyze",
    }


def analyze_conversation(payload: dict[str, Any]) -> dict[str, Any]:
    raw_text = _raw_conversation_text(payload)
    text = normalize_founder_request(raw_text)
    lowered = text.lower()
    scores = _score_modes(lowered)
    mode_key = _choose_mode(lowered, scores)
    definition = MODE_DEFINITIONS[mode_key]
    workflow_type = definition["workflow_type"]
    mission_required = workflow_type in {"implementation", "deployment", "roadmap", "security_review"}
    semantic = build_semantic_model(text, mode_key, workflow_type)
    roadmap = generate_roadmap_proposal(text, mode_key) if workflow_type == "roadmap" else None
    intelligence = {
        "mode": definition["label"],
        "mode_key": mode_key,
        "confidence": _confidence(scores, mode_key, text),
        "secondary_modes": _secondary_modes(scores, mode_key),
        "workflow_type": workflow_type,
        "mission_required": mission_required,
        "coding_required": workflow_type == "implementation",
        "deployment_required": workflow_type == "deployment",
        "founder_approval_required": mission_required,
        "executive_owner": definition["owner"],
        "departments_affected": definition["departments"],
        "normalized_request": text,
        "semantic_model": semantic,
        "decisions": semantic["decisions"],
        "actions": semantic["actions"],
        "knowledge": semantic["knowledge"],
        "mission_suggestion": _mission_suggestion(text, definition, mission_required, semantic),
        "recommended_next_action": _recommended_next_action(workflow_type),
        "roadmap_proposal": roadmap,
        "analyzed_at": _now(),
    }
    return {"company": "AI Software Factory", "product": "AI Conversation Intelligence Engine", "milestone": "CI-03", "status": "conversation-intelligence-ready", "conversation_intelligence": intelligence}


def normalize_founder_request(text: str) -> str:
    clean = str(text or "").replace("\r\n", "\n").strip()
    if not clean:
        return ""
    if _looks_like_rendered_intelligence(clean):
        extracted = _extract_from_rendered_intelligence(clean)
        if extracted:
            clean = extracted
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    return clean.strip()


def build_semantic_model(text: str, mode_key: str, workflow_type: str) -> dict[str, Any]:
    sentences = _semantic_sentences(text)
    constraints = _classify_sentences(sentences, ["do not", "never", "only", "unless", "protect", "must", "should", "approval", "small reviewable", "constitution", "no "])
    requested_actions = _classify_sentences(sentences, ["perform", "review", "audit", "identify", "verify", "produce", "generate", "implement", "fix", "deploy", "create"])
    context = _classify_sentences(sentences, ["mission control", "board room", "github", "gcp", "production", "repository", "login", "authentication", "constitution", "founder"])

    decisions = _semantic_decisions(constraints, mode_key, workflow_type)
    actions = _semantic_actions(requested_actions, mode_key, workflow_type)
    knowledge = _semantic_knowledge(context, mode_key)

    used: set[str] = set()
    decisions = _dedupe_bucket(decisions, used)[:8]
    actions = _dedupe_bucket(actions, used)[:8]
    knowledge = _dedupe_bucket(knowledge, used)[:8]
    return {
        "intent_title": _executive_title(text, mode_key),
        "intent_summary": _intent_summary(mode_key, workflow_type),
        "constraints": constraints[:8],
        "requested_outcomes": requested_actions[:8],
        "context_facts": context[:8],
        "decisions": decisions,
        "actions": actions,
        "knowledge": knowledge,
    }


def generate_roadmap_proposal(text: str, mode_key: str) -> dict[str, Any]:
    title = "Mission Control Architecture Roadmap" if mode_key == "architecture_review" else "Mission Control Engineering Roadmap"
    missions = [
        {"mission_id": "PROTECT-02", "objective": "Extend protected-boundary checks across UI shell, auth, deployment, and GitHub execution paths.", "business_value": "Reduces regressions as Mission Control becomes the primary operating interface.", "existing_components_to_reuse": ["Auth Boundary Policy", "validation gates", "GitHub Executor safety model"], "files_expected_to_change": ["app/platform/auth_boundary/*", "app/platform/code_planner/service.py"], "risks": ["Overblocking legitimate changes if mission typing is incomplete."], "validation_tests": ["python -m app.platform.auth_boundary.policy_check"], "estimated_pr_size": "small"},
        {"mission_id": "CI-04", "objective": "Add schema-backed model output for Conversation Intelligence with deterministic fallback.", "business_value": "Improves Board Room judgment while preserving predictable behavior when AI output fails.", "existing_components_to_reuse": ["Conversation Intelligence", "AI runtime", "Company Intelligence snapshot"], "files_expected_to_change": ["app/platform/conversation_intelligence/service.py", "app/platform/runtime/service.py"], "risks": ["Malformed model JSON must never break Board Room."], "validation_tests": ["python -m app.platform.conversation_intelligence.conversation_intelligence_check"], "estimated_pr_size": "medium"},
        {"mission_id": "MC-001", "objective": "Bind the active Company Constitution into Board Room, workflows, proposals, and execution planning.", "business_value": "Makes governance runtime-enforced instead of prompt-dependent.", "existing_components_to_reuse": ["Knowledge Vault KV-0001", "Board Room", "Founder Workflow Engine"], "files_expected_to_change": ["app/platform/constitution/*", "app/platform/operating_console/service.py"], "risks": ["Duplicate constitution sources if canonical artifact is not selected."], "validation_tests": ["python -m app.platform.constitution.constitution_check"], "estimated_pr_size": "medium"},
        {"mission_id": "BR-04", "objective": "Persist Board Room conversations and continue existing chats instead of forcing new chats.", "business_value": "Improves Founder experience and makes Mission Control feel like the primary company interface.", "existing_components_to_reuse": ["Operating Console", "Founder Workflow Engine", "Knowledge Vault"], "files_expected_to_change": ["app/platform/operating_console/service.py", "app/platform/ui/founder_dashboard_board_chat.py"], "risks": ["Conversation state must not expose secrets."], "validation_tests": ["frontend contract validation", "Board Room smoke test"], "estimated_pr_size": "medium"},
        {"mission_id": "WF-03", "objective": "Make workflow actions context-aware for roadmap approval, implementation approval, and deployment approval.", "business_value": "Prevents Founder from accidentally approving implementation when only roadmap review was requested.", "existing_components_to_reuse": ["Founder Workflow Engine", "Conversation Intelligence"], "files_expected_to_change": ["app/platform/founder_workflow/service.py"], "risks": ["Incorrect stage transitions could confuse Founder approval state."], "validation_tests": ["python -m app.platform.founder_workflow.workflow_check"], "estimated_pr_size": "small"},
        {"mission_id": "REPO-02", "objective": "Upgrade Repository Intelligence from static maps to live repository inspection summaries.", "business_value": "Lets Board Room verify recommendations against real code before proposing changes.", "existing_components_to_reuse": ["Repository Intelligence", "GitHub connector/executor contract"], "files_expected_to_change": ["app/platform/repository_intelligence/service.py"], "risks": ["Large repository scans must stay fast and bounded."], "validation_tests": ["repository context smoke test"], "estimated_pr_size": "medium"},
        {"mission_id": "GHE-03", "objective": "Expose GitHub access health clearly in Mission Control without showing secret values.", "business_value": "Founder can see whether live execution is ready before approving PR automation.", "existing_components_to_reuse": ["GitHub Executor", "Runtime Secret Manager status"], "files_expected_to_change": ["app/platform/github_execution/service.py", "app/platform/ui/*"], "risks": ["Must never log or render token values."], "validation_tests": ["GitHub executor dry-run status check"], "estimated_pr_size": "small"},
        {"mission_id": "QA-02", "objective": "Add production smoke tests for login, dashboard, Board Room, workflow generation, and rollback readiness.", "business_value": "Catches regressions before Cloud Run traffic shifts.", "existing_components_to_reuse": ["login boundary check", "dashboard script boundary check", "Cloud Run runbook"], "files_expected_to_change": ["app/platform/auth/*", "infra/scripts/*"], "risks": ["Smoke tests must be deterministic and not require live secrets."], "validation_tests": ["python -m app.platform.auth.login_boundary_check"], "estimated_pr_size": "medium"},
        {"mission_id": "AEL-02", "objective": "Connect Executive Intelligence to active workflows, blockers, PRs, and deployment state.", "business_value": "Turns Mission Control from pages into a company operating dashboard.", "existing_components_to_reuse": ["Executive Intelligence", "Company Intelligence", "Founder Workflow Engine"], "files_expected_to_change": ["app/platform/executive_intelligence/*", "app/platform/company_intelligence/service.py"], "risks": ["Stale intelligence must be marked clearly."], "validation_tests": ["python -m app.platform.executive_intelligence.executive_intelligence_check"], "estimated_pr_size": "medium"},
        {"mission_id": "UI-02", "objective": "Continue extracting Board Room UI from inline string replacement into maintainable templates/static JS.", "business_value": "Reduces UI regressions and makes future Founder Experience work safer.", "existing_components_to_reuse": ["auth-safe renderer", "dashboard script boundary check"], "files_expected_to_change": ["app/platform/ui/*"], "risks": ["Must not touch auth/session shell unless explicitly scoped."], "validation_tests": ["dashboard script boundary check", "frontend build validation"], "estimated_pr_size": "medium"},
    ]
    return {"title": title, "status": "roadmap-proposal-ready-for-founder-review", "implementation_allowed": False, "founder_approval_meaning": "Approve roadmap for planning only; implementation still requires separate mission approval.", "missions": missions}


def _raw_conversation_text(payload: dict[str, Any]) -> str:
    parts = []
    for key in ("message", "request", "prompt", "transcript"):
        value = payload.get(key)
        if value:
            parts.append(str(value))
    return "\n".join(parts).strip()


def _looks_like_rendered_intelligence(text: str) -> bool:
    lowered = text.lower()
    marker_count = sum(1 for marker in UI_PANEL_MARKERS if marker in lowered)
    return marker_count >= 3


def _extract_from_rendered_intelligence(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    useful: list[str] = []
    skip = {"conversation intelligence", "mode", "decisions", "actions", "knowledge", "send generate workflow", "mission suggested", "workflow generated"}
    for line in lines:
        lowered = line.lower()
        if lowered in skip or lowered.startswith("generate workflow") or lowered.startswith("suggested:") or lowered.startswith("create proposal"):
            continue
        if any(fragment in lowered for fragment in ["ask founder to approve", "founder should approve", "waiting-founder-action"]):
            continue
        if len(line) > 18:
            useful.append(line)
    return "\n".join(_unique(useful))


def _score_modes(lowered: str) -> dict[str, int]:
    scores = {key: 0 for key in MODE_DEFINITIONS}
    if _contains(lowered, ROADMAP_TRIGGERS):
        scores["engineering_roadmap"] += 7
    if _contains(lowered, ARCHITECTURE_TRIGGERS):
        scores["architecture_review"] += 6
    if _contains(lowered, IMPLEMENTATION_TRIGGERS):
        scores["implementation"] += 3
    if _contains(lowered, DEPLOYMENT_TRIGGERS):
        scores["deployment"] += 2
    if _contains(lowered, AUTH_TRIGGERS):
        scores["security_auth"] += 2
    if _contains(lowered, STRATEGY_TRIGGERS):
        scores["strategy"] += 3
    if _contains(lowered, PRODUCT_TRIGGERS):
        scores["product"] += 2
    if _contains(lowered, RESEARCH_TRIGGERS):
        scores["research"] += 2
    if _contains(lowered, KNOWLEDGE_TRIGGERS):
        scores["knowledge"] += 3
    if "do not implement" in lowered or "only produce" in lowered:
        scores["implementation"] = max(0, scores["implementation"] - 5)
        scores["deployment"] = max(0, scores["deployment"] - 4)
    if "github execution" in lowered or "deployment" in lowered:
        scores["deployment"] = max(0, scores["deployment"] - 1)
    return scores


def _choose_mode(lowered: str, scores: dict[str, int]) -> str:
    if _contains(lowered, ROADMAP_TRIGGERS) and _contains(lowered, ARCHITECTURE_TRIGGERS):
        return "architecture_review"
    if "do not implement" in lowered or "only produce" in lowered:
        return "architecture_review" if scores["architecture_review"] > 0 else "engineering_roadmap"
    if _contains(lowered, ROADMAP_TRIGGERS):
        return "engineering_roadmap"
    best = max(scores, key=lambda key: scores[key])
    return best if scores[best] > 0 else "general"


def _contains(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def _confidence(scores: dict[str, int], mode_key: str, text: str) -> float:
    score = scores.get(mode_key, 0)
    confidence = 0.58 + min(score, 8) * 0.045
    if len(text) > 300:
        confidence += 0.08
    if mode_key in {"architecture_review", "engineering_roadmap"}:
        confidence += 0.08
    return round(min(confidence, 0.97), 2)


def _secondary_modes(scores: dict[str, int], mode_key: str) -> list[str]:
    ranked = sorted(((key, value) for key, value in scores.items() if key != mode_key and value > 0), key=lambda item: item[1], reverse=True)
    return [MODE_DEFINITIONS[key]["label"] for key, _ in ranked[:3]]


def _semantic_decisions(constraints: list[str], mode_key: str, workflow_type: str) -> list[str]:
    decisions: list[str] = []
    if workflow_type == "roadmap":
        decisions.append("Roadmap approval is planning-only and does not authorize implementation.")
    if any("do not implement" in item.lower() or "only produce" in item.lower() for item in constraints):
        decisions.append("Do not implement code during this workflow.")
    if any("authentication" in item.lower() or "login" in item.lower() or "session" in item.lower() for item in constraints):
        decisions.append("Authentication, login, and session handling remain protected unless explicitly scoped.")
    if any("small reviewable pr" in item.lower() or "independently deployable" in item.lower() for item in constraints):
        decisions.append("Each future mission must be a small independently deployable PR.")
    if any("constitution" in item.lower() or "founder approval" in item.lower() for item in constraints):
        decisions.append("Follow the AI Software Factory Constitution and Founder approval workflow.")
    return decisions or ["Continue as executive discussion without execution."]


def _semantic_actions(actions: list[str], mode_key: str, workflow_type: str) -> list[str]:
    result: list[str] = []
    if mode_key == "architecture_review":
        result.extend(["Review Mission Control architecture and Founder experience.", "Identify architectural debt, duplicates, and temporary code.", "Produce a prioritized roadmap of 10 engineering missions."])
    elif workflow_type == "roadmap":
        result.extend(["Generate prioritized mission roadmap.", "Prepare roadmap for Founder review."])
    elif workflow_type == "implementation":
        result.append("Create implementation plan after repository audit and Founder approval.")
    elif workflow_type == "deployment":
        result.append("Prepare deployment workflow and require explicit deployment approval.")
    for item in actions:
        if "verify" in item.lower() and "repository" in item.lower():
            result.append("Verify recommendations against repository evidence before proposing changes.")
    return result or actions[:5]


def _semantic_knowledge(context: list[str], mode_key: str) -> list[str]:
    result: list[str] = []
    if any("mission control" in item.lower() for item in context):
        result.append("Mission Control is the primary operating interface under review.")
    if any("production" in item.lower() for item in context):
        result.append("Review is against current production and repository state.")
    if any("github" in item.lower() for item in context):
        result.append("Workflow includes GitHub execution and PR lifecycle concerns.")
    if any("login" in item.lower() or "authentication" in item.lower() for item in context):
        result.append("Authentication boundary is a protected production-stability concern.")
    if mode_key == "architecture_review":
        result.append("Founder is requesting architectural review, not immediate deployment.")
    return result or context[:5]


def _mission_suggestion(text: str, definition: dict[str, Any], mission_required: bool, semantic: dict[str, Any]) -> dict[str, Any]:
    if not mission_required:
        return {"suggested": False, "title": None, "reason": "Conversation can remain a working note."}
    label = str(definition["label"])
    return {"suggested": True, "title": f"{label}: {semantic['intent_title']}", "workflow_type": definition["workflow_type"], "reason": "Founder requested a roadmap/review workflow, not immediate implementation." if definition["workflow_type"] == "roadmap" else "Founder intent requires an approval-gated workflow."}


def _recommended_next_action(workflow_type: str) -> str:
    if workflow_type == "roadmap":
        return "Generate roadmap workflow for Founder review. Approval means approve planning only, not implementation."
    if workflow_type == "implementation":
        return "Generate implementation workflow and require Founder approval before repository mutation."
    if workflow_type == "deployment":
        return "Generate deployment workflow and require explicit deployment approval."
    if workflow_type == "knowledge_note":
        return "Continue discussion or save as knowledge note."
    return "Continue discussion or save as working note."


def _semantic_sentences(text: str) -> list[str]:
    raw = re.split(r"[\n.]+", text)
    cleaned = []
    for sentence in raw:
        clean = " ".join(sentence.strip(" -•\t0123456789.").split())
        if len(clean) > 8:
            cleaned.append(clean)
    return _unique(cleaned)


def _classify_sentences(sentences: list[str], needles: list[str]) -> list[str]:
    return [sentence for sentence in sentences if any(needle in sentence.lower() for needle in needles)]


def _dedupe_bucket(items: list[str], used: set[str]) -> list[str]:
    out: list[str] = []
    for item in _unique(items):
        key = _semantic_key(item)
        if key not in used:
            used.add(key)
            out.append(item)
    return out


def _semantic_key(text: str) -> str:
    lowered = re.sub(r"[^a-z0-9 ]", "", text.lower())
    lowered = re.sub(r"\b(the|a|an|and|or|to|of|for|with|current)\b", " ", lowered)
    return " ".join(lowered.split())[:90]


def _executive_title(text: str, mode_key: str) -> str:
    lowered = text.lower()
    if mode_key == "architecture_review" and "mission control" in lowered:
        return "Mission Control Executive Architecture Review"
    if mode_key == "engineering_roadmap":
        return "Executive Engineering Roadmap"
    if mode_key == "security_auth":
        return "Authentication Boundary Review"
    clean = " ".join(text.split())
    return clean[:72].strip(" .") or "Founder workflow"


def _intent_summary(mode_key: str, workflow_type: str) -> str:
    if mode_key == "architecture_review":
        return "Founder wants an architecture review and prioritized roadmap, not immediate implementation."
    if workflow_type == "roadmap":
        return "Founder wants a planning roadmap before selecting implementation work."
    if workflow_type == "implementation":
        return "Founder wants implementation work after approval."
    if workflow_type == "deployment":
        return "Founder wants deployment workflow review."
    return "Founder is having a general or knowledge conversation."


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        normalized = _semantic_key(item)
        if normalized and normalized not in seen:
            seen.add(normalized)
            out.append(item)
    return out


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
