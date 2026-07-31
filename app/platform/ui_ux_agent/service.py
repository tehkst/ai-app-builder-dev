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
# Keywords here must name Jarvis/Board Room explicitly rather than generic UI terms
# like "chat box" or "send button" alone - those appear in requests about *other*
# chat interfaces too (e.g. a customer-facing page's own chat box), and a bare
# substring match would silently misroute those to this file instead of degrading
# cleanly to "not resolved".
KNOWN_TARGETS = {
    "app/platform/ui/founder_dashboard_board_chat.py": (
        "jarvis chat", "jarvis's chat", "board room chat", "message jarvis",
    ),
}

# Every KNOWN_TARGETS entry must have a matching entry here: the real function that
# renders that file's page, whether production wraps it with the Jarvis runtime
# enhancement layer (which injects things like the existing attach-file button),
# whether the page is gated behind founder login (so the preview needs a fake-auth
# init script to reach the actual authenticated content instead of just the login
# screen), and the URL fragment that routes the single-page app to the relevant
# section. This is what lets the preview show the REAL merged page - including any
# functionality that already exists at runtime - instead of a description the model
# invents on its own, which has no way to know what's already there and can propose
# duplicates of existing functionality without anyone noticing until a human reads
# raw code.
PREVIEW_ENTRYPOINTS = {
    "app/platform/ui/founder_dashboard_board_chat.py": ("render_board_chat_dashboard", True, True, "#board"),
}

# Bypasses ONLY the client-side login gate inside the isolated, throwaway preview
# server (never touches production auth) so the screenshot shows the real
# authenticated page instead of the login screen. Installed via Playwright's
# add_init_script, which runs before any page script on every navigation.
_AUTH_BYPASS_INIT_SCRIPT = """
localStorage.setItem('mission_control_token', 'ui-ux-preview-token');
(function(){
  var realFetch = window.fetch.bind(window);
  window.fetch = function(url, opts){
    if (typeof url === 'string' && url.indexOf('/mission-control/auth/session') >= 0) {
      return Promise.resolve(new Response(JSON.stringify({authenticated: true}), {
        status: 200, headers: {'Content-Type': 'application/json'}
      }));
    }
    return realFetch(url, opts);
  };
})();
"""

SYSTEM_PROMPT = (
    "You are a UI/UX specialist agent for a software platform. You are given the exact "
    "current content of one source file and a founder's change request. Respond with ONLY "
    "a JSON object, no prose, shaped as:\n"
    '{"sow": ["bullet describing exactly what will change", "..."], '
    '"search_text": "<a short, exact, unique substring copied verbatim from the current file '
    'that anchors where the change goes>", '
    '"replace_text": "<the replacement text for that exact substring>"}\n'
    "search_text must appear verbatim and exactly once in the current file content - copy it "
    "character-for-character, do not paraphrase it. Keep the change minimal and scoped to what "
    "was actually requested. Before proposing a new UI element (a button, field, panel, etc.), "
    "check whether the current file content already implements it - do not propose adding "
    "something that already exists, even under a different label.\n\n"
    "Design and motion rules, apply whenever the change touches animation, transitions, or "
    "visual layout:\n"
    "- Earn every animation: never animate 100+/day actions (keyboard shortcuts, command "
    "palettes); minimize motion on tens/day actions (hover, list nav); modals/drawers/toasts "
    "get standard motion; rare, first-time moments (onboarding, success) can carry more polish.\n"
    "- Never use ease-in on UI - it reads as sluggish. Entering/exiting elements: ease-out. "
    "Elements moving or morphing on-screen: ease-in-out. Hover/color changes: ease. Only "
    "marquees/progress bars: linear.\n"
    "- Keep UI animation under 300ms: button press ~100-160ms, tooltips/small popovers "
    "~125-200ms, dropdowns/selects ~150-250ms, modals/drawers ~200-500ms.\n"
    "- Popovers, dropdowns, and tooltips must set transform-origin to the element that "
    "triggered them, never center; modals stay centered.\n"
    "- Never start an entrance from scale(0) or a bare opacity fade with no transform - start "
    "from scale(0.9-0.97) plus opacity 0.\n"
    "- Only animate transform and opacity for performance; never width, height, margin, "
    "padding, top, or left.\n"
    "- Respect prefers-reduced-motion: keep opacity/color transitions, drop movement, "
    "position, and scale animations. Gate hover-triggered motion behind "
    "(hover: hover) and (pointer: fine).\n"
    "- Visual hierarchy: make the single most important element on screen the most obvious "
    "one via spacing, contrast, and size rather than competing elements; group related "
    "controls by proximity; prefer specific labels over vague ones."
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
    preview = _render_preview(target_file, proposed_content)

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


MAX_DRAFT_ATTEMPTS = 3
_RETRYABLE_ANCHOR_STATUSES = {"anchor_not_found", "anchor_ambiguous", "draft_parse_error", "draft_incomplete"}


def _draft_change(target_file: str, current_content: str, change_request: str) -> Dict[str, Any]:
    base_prompt = (
        "Target file: %s\n\nCurrent file content:\n```\n%s\n```\n\nFounder's change request:\n%s"
        % (target_file, current_content, change_request)
    )
    prompt = base_prompt
    attempt: Dict[str, Any] = {}
    for tries in range(1, MAX_DRAFT_ATTEMPTS + 1):
        attempt = _draft_attempt(prompt, current_content, target_file)
        if attempt["status"] in _RETRYABLE_ANCHOR_STATUSES:
            # LLMs occasionally paraphrase instead of copying search_text verbatim. Retrying
            # with the exact failure and the model's own bad anchor spelled out fixes this far
            # more often than dead-ending on the first miss, without weakening the exact-match
            # check itself.
            if tries == MAX_DRAFT_ATTEMPTS:
                return attempt
            prompt = base_prompt + "\n\nYour previous attempt failed: %s%s Copy search_text character-for-character from the current file content shown above." % (
                attempt.get("error") or attempt["status"],
                (" The text you returned was: %r." % attempt.get("attempted_search_text")) if attempt.get("attempted_search_text") else "",
            )
            continue
        if attempt["status"] != "ok":
            return attempt

        # The anchor was found and applied cleanly - now confirm the edit actually changes
        # anything a founder would see, before ever presenting it as a working solution.
        verification = _verify_visible_change(target_file, current_content, attempt["search_text"], attempt["replace_text"])
        if verification["status"] in {"visible", "unverifiable"}:
            return attempt
        if tries == MAX_DRAFT_ATTEMPTS:
            attempt = dict(attempt)
            attempt["status"] = "no_visible_change"
            attempt["error"] = verification.get("error")
            return attempt
        prompt = base_prompt + (
            "\n\nYour previous attempt applied cleanly (search_text: %r -> replace_text: %r) but "
            "produced NO detectable visual difference when the page was rendered before and after "
            "the change and compared. This usually means the property you changed is not the real "
            "constraint on that element's appearance - for example editing min-width when padding "
            "or font-size already make the element bigger, or a value a later stylesheet "
            "re-declares. Look again at ALL CSS rules (including shared/base classes) that could "
            "affect the targeted element, and make a change that will actually be visible."
            % (attempt["search_text"], attempt["replace_text"])
        )
    return attempt


def _draft_attempt(prompt: str, current_content: str, target_file: str) -> Dict[str, Any]:
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
    if not search_text or replace_text is None:
        return {"status": "draft_incomplete", "error": "The model's response was missing a required field."}
    occurrences = current_content.count(search_text)
    if occurrences == 0:
        return {"status": "anchor_not_found", "error": "Could not locate an exact anchor for this change in the file.", "attempted_search_text": search_text}
    if occurrences > 1:
        return {"status": "anchor_ambiguous", "error": "The proposed anchor text appears more than once in the file.", "attempted_search_text": search_text}

    sow_markdown = "\n".join("- %s" % str(item) for item in sow_items) if isinstance(sow_items, list) else str(sow_items or "")
    return {
        "status": "ok",
        "search_text": search_text,
        "replace_text": str(replace_text),
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


def _render_preview(target_file: str, proposed_content: str) -> Dict[str, Any]:
    """Render the REAL page the proposed change would produce, not a model-imagined mockup.

    This loads proposed_content as an actual Python module (in isolation, never touching
    the real cached module the running server uses) and calls its real render function, so
    a change that duplicates existing functionality or breaks the page shows up here - the
    same way it would in production - instead of only in a description the model invented.
    """
    return _render_and_verify(target_file, proposed_content, capture_layout_metrics=False)


def _render_and_verify(target_file: str, content: str, *, capture_layout_metrics: bool) -> Dict[str, Any]:
    entrypoint = PREVIEW_ENTRYPOINTS.get(target_file)
    if entrypoint is None:
        return {"status": "failed", "error": "No preview renderer is registered for %s." % target_file}
    function_name, wrap_with_jarvis, requires_auth_bypass, url_fragment = entrypoint

    try:
        html = _render_real_page(target_file, content, function_name, wrap_with_jarvis)
    except Exception as exc:
        return {"status": "failed", "error": "Rendering the modified file failed: %s: %s" % (type(exc).__name__, exc)}

    import tempfile

    try:
        with tempfile.TemporaryDirectory(prefix="ui-ux-preview-") as directory:
            index_path = Path(directory) / "index.html"
            index_path.write_text(html, encoding="utf-8")
            verification_payload: Dict[str, Any] = {
                "source_directory": directory,
                "entry_file": "index.html%s" % url_fragment,
                "capture_layout_metrics": capture_layout_metrics,
            }
            if requires_auth_bypass:
                verification_payload["init_script"] = _AUTH_BYPASS_INIT_SCRIPT
            return execute_ui_ux_verification(verification_payload)
    except Exception as exc:
        return {"status": "failed", "error": type(exc).__name__}


def _verify_visible_change(target_file: str, current_content: str, search_text: str, replace_text: str) -> Dict[str, Any]:
    """Render the page before AND after the proposed edit and compare real layout metrics.

    A change that compiles and applies cleanly can still do nothing visible - e.g. editing a
    CSS property a later stylesheet re-declares, or one that was never the actual constraint
    on an element's size (min-width when padding/font-size already make it bigger). Comparing
    real computed layout before vs after is what actually catches this, rather than trusting
    that "it rendered without errors" means the founder will see what the SOW promised.
    """
    before = _render_and_verify(target_file, current_content, capture_layout_metrics=True)
    if before.get("status") == "failed" and before.get("layout_metrics") is None:
        return {"status": "unverifiable", "error": before.get("error")}
    proposed_content = current_content.replace(search_text, replace_text, 1)
    after = _render_and_verify(target_file, proposed_content, capture_layout_metrics=True)
    if after.get("status") == "failed" and after.get("layout_metrics") is None:
        return {"status": "unverifiable", "error": after.get("error")}

    before_metrics = before.get("layout_metrics") or {}
    after_metrics = after.get("layout_metrics") or {}
    if before_metrics == after_metrics:
        return {
            "status": "no_visible_change",
            "error": "The rendered page is pixel-for-pixel identical before and after this change - "
            "no element's position, size, or style actually differs.",
        }
    return {"status": "visible", "before_metrics": before_metrics, "after_metrics": after_metrics}


def _render_real_page(target_file: str, proposed_content: str, function_name: str, wrap_with_jarvis: bool) -> str:
    import importlib.util
    import tempfile

    with tempfile.TemporaryDirectory(prefix="ui-ux-module-") as directory:
        module_path = Path(directory) / Path(target_file).name
        module_path.write_text(proposed_content, encoding="utf-8")
        spec = importlib.util.spec_from_file_location("_ui_ux_preview_module", module_path)
        if spec is None or spec.loader is None:
            raise ImportError("Could not load %s as a module for preview." % target_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

    html = getattr(module, function_name)()
    if wrap_with_jarvis:
        from app.platform.ui.jarvis_experience import enhance_dashboard_with_jarvis

        html = enhance_dashboard_with_jarvis(html)
    return html


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
