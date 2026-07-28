from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from app.platform.auth.service import require_founder
from app.platform.digital_twin.ui_verification import execute_ui_ux_verification
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformUiUxProposal
from app.platform.runtime.ai_provider import AIProviderError
from app.platform.runtime.provider_router import invoke_provider
from app.platform.ui_ux_agent import CONTRACT

REPO_ROOT = Path(__file__).resolve().parents[3]

# Deliberately small and explicit for now: only requests recognizably about the
# Jarvis/Board Room chat box resolve automatically. Broader free-text-to-file
# resolution is a follow-up once this pattern is proven, not something to guess at
# silently - an unresolved request degrades cleanly rather than picking a wrong file.
KNOWN_TARGETS = {
    "app/platform/ui/founder_dashboard_board_chat.py": (
        "chat box", "chat window", "message box", "jarvis chat", "board room chat",
        "send button", "message jarvis",
    ),
}

SYSTEM_PROMPT = (
    "You are a UI/UX specialist agent for a software platform. You are given the exact "
    "current content of one source file and a founder's change request. Respond with ONLY "
    "a JSON object, no prose, shaped as:\n"
    '{"sow": ["bullet describing exactly what will change", "..."], '
    '"search_text": "<a short, exact, unique substring copied verbatim from the current file '
    'that anchors where the change goes>", '
    '"replace_text": "<the replacement text for that exact substring>", '
    '"preview_html": "<a small, self-contained, static HTML document (inline <style> only, no '
    'scripts) that visually mocks up just the changed UI element as it will look after the '
    'change, so a human can see it without running the whole application>"}\n'
    "search_text must appear verbatim and exactly once in the current file content - copy it "
    "character-for-character, do not paraphrase it. Keep the change minimal and scoped to what "
    "was actually requested."
)


def propose_ui_change(payload: Dict[str, Any]) -> Dict[str, Any]:
    founder = require_founder(payload)
    if not founder.get("authorized"):
        return _unauthorised()

    change_request = str(payload.get("change_request") or "").strip()
    if not change_request:
        return {"contract": CONTRACT, "status": "invalid", "error": "change_request is required."}
    target_file = str(payload.get("target_file") or "").strip() or resolve_target_file(change_request)
    if not target_file:
        return {
            "contract": CONTRACT,
            "status": "target_not_resolved",
            "error": "I could not tell which UI element this refers to. Try naming it more specifically, "
            "or pass target_file explicitly.",
        }
    current_content = _read_target_file(target_file)
    if current_content is None:
        return {"contract": CONTRACT, "status": "target_not_found", "error": "%s does not exist." % target_file}

    draft = _draft_change(target_file, current_content, change_request)
    if draft.get("status") != "ok":
        return {"contract": CONTRACT, "status": draft["status"], "error": draft.get("error")}

    return _finalize_proposal(
        founder=founder,
        conversation_id=str(payload.get("conversation_id") or ""),
        target_file=target_file,
        change_request=change_request,
        current_content=current_content,
        draft=draft,
        iteration=1,
    )


def iterate_ui_change(payload: Dict[str, Any]) -> Dict[str, Any]:
    founder = require_founder(payload)
    if not founder.get("authorized"):
        return _unauthorised()

    proposal_id = str(payload.get("proposal_id") or "").strip()
    feedback = str(payload.get("feedback") or "").strip()
    if not feedback:
        return {"contract": CONTRACT, "status": "invalid", "error": "feedback is required."}

    create_platform_tables()
    with PlatformSessionLocal() as db:
        prior = db.query(PlatformUiUxProposal).filter(PlatformUiUxProposal.proposal_id == proposal_id).first()
        if prior is None:
            return {"contract": CONTRACT, "status": "not_found", "proposal_id": proposal_id}
        target_file = prior.target_file
        conversation_id = prior.conversation_id
        prior_sow = prior.sow_markdown
        iteration = prior.iteration + 1

    current_content = _read_target_file(target_file)
    if current_content is None:
        return {"contract": CONTRACT, "status": "target_not_found", "error": "%s does not exist." % target_file}

    combined_request = (
        "Original request: %s\n\nPrevious proposal summary:\n%s\n\nFounder feedback on that proposal: %s"
        % (payload.get("change_request") or "the original UI change", prior_sow, feedback)
    )
    draft = _draft_change(target_file, current_content, combined_request)
    if draft.get("status") != "ok":
        return {"contract": CONTRACT, "status": draft["status"], "error": draft.get("error")}

    return _finalize_proposal(
        founder=founder,
        conversation_id=conversation_id or "",
        target_file=target_file,
        change_request=combined_request,
        current_content=current_content,
        draft=draft,
        iteration=iteration,
    )


def approve_ui_change(payload: Dict[str, Any]) -> Dict[str, Any]:
    founder = require_founder(payload)
    if not founder.get("authorized"):
        return _unauthorised()

    proposal_id = str(payload.get("proposal_id") or "").strip()
    create_platform_tables()
    with PlatformSessionLocal() as db:
        proposal = db.query(PlatformUiUxProposal).filter(PlatformUiUxProposal.proposal_id == proposal_id).first()
        if proposal is None:
            return {"contract": CONTRACT, "status": "not_found", "proposal_id": proposal_id}
        if proposal.status not in {"proposed"}:
            return {"contract": CONTRACT, "status": "invalid_state", "error": "Proposal is %s, not awaiting approval." % proposal.status}
        target_file = proposal.target_file
        proposed_content = proposal.proposed_content
        sow_markdown = proposal.sow_markdown

    from app.platform.github_execution.approved_executor import execute_approved_github_execution

    branch_name = "ui-ux/%s" % uuid.uuid4().hex[:12]
    execution_payload = dict(payload)
    execution_payload.update({
        "mission_id": "UI-UX-%s" % proposal_id,
        "title": "UI/UX change: %s" % target_file,
        "branch_name": branch_name,
        "commit_message": "Apply founder-approved UI/UX change to %s" % target_file,
        "pr_title": "UI/UX change: %s" % target_file,
        "pr_body": sow_markdown,
        "file_changes": [{"path": target_file, "operation": "update", "content": proposed_content}],
        "live_execution": True,
    })
    result = execute_approved_github_execution(execution_payload)

    with PlatformSessionLocal() as db:
        proposal = db.query(PlatformUiUxProposal).filter(PlatformUiUxProposal.proposal_id == proposal_id).first()
        if result.get("status") == "pull-request-created":
            proposal.status = "pr_created"
            proposal.pull_request_url = result.get("pull_request_url")
            proposal.pull_request_number = result.get("pull_request_number")
        db.commit()

    if result.get("status") == "pull-request-created":
        message = (
            "Pull request created for %s: %s. It still needs the usual founder-approved merge and deploy "
            "before this reaches production." % (target_file, result.get("pull_request_url"))
        )
    else:
        message = "Could not create the pull request: %s" % (result.get("error") or result.get("status"))
    return {"contract": CONTRACT, "proposal_id": proposal_id, "message": message, "execution": result}


def reject_ui_change(payload: Dict[str, Any]) -> Dict[str, Any]:
    founder = require_founder(payload)
    if not founder.get("authorized"):
        return _unauthorised()

    proposal_id = str(payload.get("proposal_id") or "").strip()
    create_platform_tables()
    with PlatformSessionLocal() as db:
        proposal = db.query(PlatformUiUxProposal).filter(PlatformUiUxProposal.proposal_id == proposal_id).first()
        if proposal is None:
            return {"contract": CONTRACT, "status": "not_found", "proposal_id": proposal_id}
        proposal.status = "rejected"
        db.commit()
    return {"contract": CONTRACT, "status": "rejected", "proposal_id": proposal_id, "message": "Proposal rejected. No changes were made."}


def resolve_target_file(change_request: str) -> Optional[str]:
    normalized = change_request.lower()
    for target_file, keywords in KNOWN_TARGETS.items():
        if any(keyword in normalized for keyword in keywords):
            return target_file
    return None


def _finalize_proposal(
    *,
    founder: Dict[str, Any],
    conversation_id: str,
    target_file: str,
    change_request: str,
    current_content: str,
    draft: Dict[str, Any],
    iteration: int,
) -> Dict[str, Any]:
    proposed_content = current_content.replace(draft["search_text"], draft["replace_text"], 1)
    preview = _render_preview(draft["preview_html"])

    proposal_id = "UIUX-%s" % uuid.uuid4().hex[:16].upper()
    create_platform_tables()
    with PlatformSessionLocal() as db:
        row = PlatformUiUxProposal(
            proposal_id=proposal_id,
            conversation_id=conversation_id or None,
            target_file=target_file,
            change_request=change_request,
            sow_markdown=draft["sow_markdown"],
            search_text=draft["search_text"],
            replace_text=draft["replace_text"],
            proposed_content=proposed_content,
            screenshot_base64=preview.get("screenshot_base64"),
            console_errors_json=json.dumps(preview.get("console_errors") or []),
            status="proposed",
            iteration=iteration,
            requested_by=founder.get("email") or "founder",
        )
        db.add(row)
        db.commit()

    return {
        "contract": CONTRACT,
        "status": "proposed",
        "proposal_id": proposal_id,
        "target_file": target_file,
        "sow_markdown": draft["sow_markdown"],
        "screenshot_base64": preview.get("screenshot_base64"),
        "preview_status": preview.get("status"),
        "preview_error": preview.get("error"),
        "iteration": iteration,
    }


def _draft_change(target_file: str, current_content: str, change_request: str) -> Dict[str, Any]:
    prompt = (
        "Target file: %s\n\nCurrent file content:\n```\n%s\n```\n\nFounder's change request:\n%s"
        % (target_file, current_content, change_request)
    )
    try:
        result = invoke_provider(provider=None, prompt=prompt, system=SYSTEM_PROMPT, model=None)
    except AIProviderError as exc:
        return {"status": "provider_error", "error": str(exc)}
    if result.status != "completed":
        return {"status": "provider_error", "error": result.output_text or result.status}

    parsed = _parse_draft_output(result.output_text)
    if parsed is None:
        return {"status": "draft_parse_error", "error": "The model's response was not valid JSON."}
    search_text = str(parsed.get("search_text") or "")
    replace_text = parsed.get("replace_text")
    sow_items = parsed.get("sow")
    preview_html = str(parsed.get("preview_html") or "")
    if not search_text or replace_text is None or not preview_html:
        return {"status": "draft_incomplete", "error": "The model's response was missing a required field."}
    occurrences = current_content.count(search_text)
    if occurrences == 0:
        return {"status": "anchor_not_found", "error": "Could not locate an exact anchor for this change in the file."}
    if occurrences > 1:
        return {"status": "anchor_ambiguous", "error": "The proposed anchor text appears more than once in the file."}

    sow_markdown = "\n".join("- %s" % str(item) for item in sow_items) if isinstance(sow_items, list) else str(sow_items or "")
    return {
        "status": "ok",
        "search_text": search_text,
        "replace_text": str(replace_text),
        "preview_html": preview_html,
        "sow_markdown": sow_markdown or "- Proposed change to %s" % target_file,
    }


def _parse_draft_output(output_text: str) -> Optional[Dict[str, Any]]:
    candidate = output_text.strip()
    match = re.search(r"\{.*\}", candidate, re.DOTALL)
    if match:
        candidate = match.group(0)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _render_preview(preview_html: str) -> Dict[str, Any]:
    import tempfile

    try:
        with tempfile.TemporaryDirectory(prefix="ui-ux-preview-") as directory:
            index_path = Path(directory) / "index.html"
            index_path.write_text(preview_html, encoding="utf-8")
            return execute_ui_ux_verification({"source_directory": directory, "entry_file": "index.html"})
    except Exception as exc:
        return {"status": "failed", "error": type(exc).__name__}


def _read_target_file(target_file: str) -> Optional[str]:
    safe = _safe_relative_path(target_file)
    if safe is None:
        return None
    resolved = REPO_ROOT / safe
    if not resolved.is_file():
        return None
    return resolved.read_text(encoding="utf-8")


def _safe_relative_path(path: str) -> Optional[str]:
    if not path or path.startswith("/") or "\\" in path:
        return None
    candidate = Path(path)
    if any(part in {"", ".", ".."} for part in candidate.parts):
        return None
    safe = candidate.as_posix()
    resolved = (REPO_ROOT / safe).resolve()
    try:
        resolved.relative_to(REPO_ROOT)
    except ValueError:
        return None
    return safe


def _unauthorised() -> Dict[str, Any]:
    return {
        "contract": CONTRACT,
        "status": "unauthorised",
        "authenticated": False,
        "error": "Founder authentication is required for UI/UX proposals.",
    }
