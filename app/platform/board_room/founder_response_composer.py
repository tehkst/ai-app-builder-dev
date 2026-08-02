from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.platform.board_room.founder_conversation_contract import ConversationContract


_INTERNAL_PATTERNS = (
    "derived_from_canonical_operational_evidence",
    "derived_from_canonical_gates",
    "context_snapshot",
    "executive_reasoning",
    "routing policy",
    "project progress: {",
    "'gates': [",
    '"gates": [',
)


@dataclass(frozen=True)
class FounderResponse:
    text: str
    decisions: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    mission_proposals: List[Dict[str, Any]]
    knowledge: List[Dict[str, Any]]
    validation: Dict[str, Any]
    fallback_used: bool


class FounderResponseComposer:
    """Validates and repairs founder-visible output without exposing reasoning."""

    FALLBACK_FAMILIES = {
        "PRODUCT_DISCOVERY", "STRATEGIC_ADVICE", "BRAINSTORMING", "SYSTEM_REVIEW",
        "ARCHITECTURE_EXPLANATION", "ARCHITECTURE_REVIEW",
        "CAPABILITY_DESCRIPTION", "CAPABILITY_COMPARISON", "STATUS_REQUEST",
        "TROUBLESHOOTING", "PROJECT_PLANNING", "EXECUTION_REQUEST",
        "CONVERSATIONAL_FOLLOW_UP", "INFORMATION_REQUEST",
    }

    @classmethod
    def compose(
        cls,
        *,
        founder_message: str,
        draft: str,
        contract: ConversationContract,
        context: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> FounderResponse:
        signals = cls._quality_signals(draft)
        fallback_used = bool(signals)
        if signals:
            # Fallback templates are pre-written, deterministic prose - they can never
            # contain a leaked raw object dump or hidden-reasoning artifact, so they
            # don't need _redact()'s leak check. Applying it here was a real bug: a
            # real, legitimate module name like "executive_reasoning_engine" contains
            # the substring "executive_reasoning" (one of _INTERNAL_PATTERNS, meant to
            # catch the internal *class* name leaking into a draft) and was getting the
            # whole safe fallback answer discarded as "internal operating data".
            text = cls._fallback(founder_message, contract, context, conversation_history or [])
        else:
            text = cls._redact(draft.strip())
        artifacts = cls._artifacts(text, contract, founder_message)
        return FounderResponse(
            text=text,
            decisions=artifacts["decisions"],
            actions=artifacts["actions"],
            mission_proposals=artifacts["mission_proposals"],
            knowledge=artifacts["knowledge"],
            validation={
                "passed": not cls._quality_signals(text),
                "initial_signals": signals,
            },
            fallback_used=fallback_used,
        )

    @classmethod
    def _quality_signals(cls, text: str) -> List[str]:
        # Deliberately narrow: only real safety properties (a truly empty draft,
        # leaked internal reasoning/state, a raw object dump), never a business-
        # content-shape requirement. A prior version of this method required
        # PRODUCT_DISCOVERY answers to contain specific checklist words and
        # STRATEGIC_ADVICE answers to contain one of ten recommendation-framed
        # words ("recommend", "should", ...) - that per-mode keyword gate was the
        # confirmed, repeated cause of real founder-facing bugs (a founder asking
        # Jarvis to *evaluate and list* something got a recommendation-shaped
        # non-answer because the real, honest, on-topic answer had no reason to
        # contain those specific words). Two narrow widenings of the keyword list
        # didn't hold up live - removing the gate, not widening it again, is the
        # fix. See jarvis_live_bug_regression_check.py for the real evidence.
        lowered = text.lower().strip()
        signals = []
        if not lowered:
            signals.append("empty")
        if any(pattern in lowered for pattern in _INTERNAL_PATTERNS):
            signals.append("internal_evidence_leak")
        if text.count("{") and text.count("}") and any(term in lowered for term in ("status", "gates", "authority")):
            signals.append("raw_object")
        return signals

    @classmethod
    def _fallback(
        cls,
        message: str,
        contract: ConversationContract,
        context: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> str:
        mode = contract.mode
        if mode == "PRODUCT_DISCOVERY":
            return cls._no_verified_answer(message)
        if mode == "INFORMATION_REQUEST":
            normalized = " ".join(message.lower().split()).strip(" .!")
            if normalized in {
                "approve", "approved", "go ahead", "proceed",
                "proceed with this", "create the mission",
            }:
                return (
                    "I do not have a pending decision-ready mission in this conversation. "
                    "Tell me which recommendation you want to approve, or ask me to prepare one first."
                )
            if re.search(r"\bwhat does mvp mean\b", message.lower()):
                return (
                    "MVP means Minimum Viable Product: the smallest version of a product that solves "
                    "a real customer problem well enough to test whether people will use or pay for it. "
                    "It is not a low-quality final product; it is a focused learning version."
                )
            return "I could not verify a reliable answer from the available information. Please rephrase the specific fact you want explained."
        if mode == "ARCHITECTURE_EXPLANATION":
            return cls._architecture_explanation(context)
        if mode == "ARCHITECTURE_REVIEW":
            return cls._architecture_review(context)
        if mode == "CAPABILITY_DESCRIPTION":
            return cls._capability_description(context)
        if mode == "CAPABILITY_COMPARISON":
            return cls._capability_comparison(message)
        if mode == "STATUS_REQUEST":
            return cls._status(context)
        if mode == "SYSTEM_REVIEW":
            return cls._system_review(context)
        if mode == "EXECUTION_REQUEST":
            if cls._already_told_governed_mission_pending(history):
                return (
                    "I already flagged that this needs to go through the governed mission workflow, and I do not see "
                    "anything in this conversation showing it has progressed since then. If you approved a mission, "
                    "check Mission Execution for its current status - I cannot confirm execution progress from this "
                    "conversation alone. If it looks stuck there too, that is worth surfacing as a platform issue "
                    "rather than repeating the same request here."
                )
            return (
                "I can prepare this as a governed mission, but I have not created, implemented, or deployed anything. "
                "The safe sequence is to confirm the customer and scope, approve a mission proposal, implement and validate it, "
                "then request separate approval for deployment. The next step is to review the proposed scope."
            )
        if mode == "STRATEGIC_ADVICE":
            return cls._no_verified_answer(message)
        if mode == "BRAINSTORMING":
            return (
                "I could not generate sufficiently grounded options from the available evidence. "
                "No recommendation or action has been created."
            )
        if mode == "CONVERSATIONAL_FOLLOW_UP":
            return cls._no_verified_answer(message)
        if mode == "PROJECT_PLANNING":
            return (
                "Start with a short discovery phase, define one measurable customer outcome, scope the smallest release around it, "
                "then plan implementation and validation. Keep deployment as a separate approval-gated step."
            )
        if mode == "TROUBLESHOOTING":
            return (
                "The most likely cause cannot be confirmed from the available evidence yet. "
                "First reproduce the failure and capture the exact request, response, and relevant runtime state before changing the system."
            )
        return "I could not produce a reliable answer from the available evidence. No action has been taken."

    @staticmethod
    def _no_verified_answer(message: str) -> str:
        """The one honest, generic last-resort answer used whenever no data-grounded
        fallback applies and the real draft failed quality review (now only a truly
        empty draft, leaked internal data, or a raw object dump - see
        _quality_signals). This used to be several different hand-written, per-topic
        canned answers keyed on specific keywords from past test messages
        ("transport"+"crm", "jarvis"+"ui"+"code generation", "lovable"/"replit",
        "transport"+"50 vehicles") - a real smell (answers to specific past test
        phrasing, not the founder's actual message) and the confirmed, repeated cause
        of real founder-facing bugs (PR #522/#523, #525): whichever canned template
        happened to match looked like a disconnected non-answer to anything actually
        asked. Reflecting back a real, structural fact about the message (it
        references a URL) is not fabricated data - it is literally true of the
        message and explains why nothing verified could be given; otherwise this
        states plainly that no verified answer was produced, rather than ever
        substituting an unrelated canned recommendation again."""
        if re.search(r"https?://", message):
            return (
                "I could not produce a verified, reviewed answer to this specific request right now. "
                "Part of it depends on a URL I have no way to fetch directly - I have no live web-browsing "
                "or external-repository access in this conversation. If you connect the referenced "
                "repository (Settings) or paste the relevant details here, I can compare it against real "
                "platform data instead of guessing."
            )
        return (
            "I could not produce a verified, reviewed answer to this specific request from the "
            "available evidence right now, and I will not substitute an unrelated generic "
            "recommendation for it. Rephrase the specific question, or tell me what additional "
            "detail or access I'm missing, and I will try again."
        )

    @staticmethod
    def _system_review(context: Dict[str, Any]) -> str:
        observations = context.get("observations") or {}
        source_status = context.get("source_status") or {}
        available = [name.replace("_", " ") for name, status in source_status.items() if status not in {"unknown", "unavailable", "failed"}]
        strongest = "governed mission and deployment foundations" if available else "the documented platform architecture"
        weakest = "end-to-end product coherence and demonstrated founder outcomes"
        return (
            f"Verified from the current read models, the strongest area is {strongest}. "
            f"The available evidence sources are {', '.join(available) or 'limited'}, and they report "
            f"{observations.get('active_missions', 0)} active mission(s) and {observations.get('blocked_missions', 0)} blocked mission(s).\n\n"
            f"My inference is that the weakest area is {weakest}: capabilities exist, but their value depends on completing repeatable journeys without manual stitching. "
            "Focus next on one fully verified founder mission and use its failures to prioritize integration work."
        )

    @staticmethod
    def _architecture_explanation(context: Dict[str, Any]) -> str:
        sources = context.get("sources") or {}
        executive = sources.get("executive_intelligence") or {}
        repository = sources.get("repository_intelligence") or {}
        executive_available = str(executive.get("status") or "").lower() not in {
            "", "unknown", "unavailable", "failed",
        }
        repository_available = str(repository.get("status") or "").lower() not in {
            "", "unknown", "unavailable", "failed",
        }
        if not executive_available and not repository_available:
            return (
                "I could not retrieve enough verified architecture evidence to give you a reliable full explanation. "
                "I can confirm that Jarvis is the founder-facing conversational interface, but the current component "
                "and runtime evidence is unavailable, so I will not invent the remaining architecture."
            )
        contract = str(executive.get("state_contract_version") or "not verified")
        areas = repository.get("repository_areas") or {}
        area_names = ", ".join(str(name).replace("_", " ") for name in areas) or "not verified"
        return (
            "AI Software Factory is organized as a governed software-delivery system with Jarvis and the Founder "
            "Experience at the top. A founder message enters the Board Room, where conversation intent is classified, "
            "read-only context is retrieved, and the cognitive and executive reasoning layers compose a founder-safe "
            "answer. Informational questions remain read-only; implementation and consequential actions are routed "
            "through separate approval gates.\n\n"
            "Executive Intelligence is the canonical executive read model. Its current contract is "
            f"{contract}. It reconciles repository, mission, capability, GitHub, deployment, verification, health, "
            "release, and Board Room evidence without becoming the authority for those systems. Durable delivery state "
            "belongs to the mission runtime and its workflow and task records; UI cards and pipeline views are projections.\n\n"
            "AI generation is provider-independent. The runtime resolves the selected provider and model, calls the "
            "matching DeepSeek or OpenAI adapter, and returns one normalized response contract to Jarvis. Provider "
            "credentials remain behind the runtime boundary.\n\n"
            "Approved delivery progresses through planning, architecture and engineering authorities, code generation, "
            "workspace validation, governed repository and GitHub operations, CI, founder-approved merge and deployment, "
            "production verification, and founder acceptance. No conversational layer grants itself execution authority.\n\n"
            f"The verified repository map currently covers: {area_names}. This is a bounded read model rather than a "
            "complete proof of every deployed component, so any capability without current runtime evidence remains "
            "unverified rather than assumed."
            + FounderResponseComposer._module_dependency_paragraph(sources)
        )

    @staticmethod
    def _architecture_review(context: Dict[str, Any]) -> str:
        sources = context.get("sources") or {}
        available = [
            name.replace("_", " ")
            for name, value in sources.items()
            if str((value or {}).get("status") or "").lower()
            not in {"", "unknown", "unavailable", "failed"}
        ]
        if not available:
            return (
                "I could not retrieve enough verified architecture evidence to review the current design reliably. "
                "No architecture recommendation has been made."
            )
        return (
            "The current architecture can be reviewed from "
            + ", ".join(available)
            + ". These sources distinguish canonical authorities from read-only projections, but the bounded evidence "
            "does not by itself prove every deployed integration. I would label unverified runtime links as unknown "
            "rather than convert this review into a recommendation."
            + FounderResponseComposer._module_dependency_paragraph(sources)
        )

    @staticmethod
    def _module_dependency_paragraph(sources: Dict[str, Any]) -> str:
        """Append real module-connection evidence when the AST-derived graph was fetched.

        Kept separate from the surrounding static templates (rather than editing their
        hardcoded prose) so this stays honest about being real, bounded evidence: it
        says nothing when the source wasn't fetched or returned no modules, instead of
        padding the answer with an empty or invented paragraph.
        """
        graph = sources.get("architecture_graph") or {}
        modules = graph.get("modules") or []
        if graph.get("status") != "ready" or not modules:
            return ""
        lines = []
        for module in modules[:5]:
            imports = module.get("imports") or []
            imported_by = module.get("imported_by") or []
            detail = "%s: imports %s; imported by %s" % (
                module.get("module"),
                ", ".join(imports[:4]) or "nothing in this bounded view",
                ", ".join(imported_by[:4]) or "nothing in this bounded view",
            )
            lines.append(detail)
        return (
            "\n\nFrom the live Python-AST module dependency graph (%s of %s modules shown, selected by %s):\n- "
            % (
                graph.get("shown_module_count"),
                graph.get("total_modules_in_graph"),
                str(graph.get("selection_basis") or "").replace("-", " "),
            )
            + "\n- ".join(lines)
        )

    @staticmethod
    def _capability_description(context: Dict[str, Any]) -> str:
        sources = context.get("sources") or {}
        if not sources:
            return (
                "I could not retrieve enough current capability evidence to give you a reliable complete inventory. "
                "I can describe confirmed capabilities once the read-only platform evidence is available."
            )
        return (
            "Jarvis can discuss strategy and product decisions, inspect read-only platform evidence, prepare governed "
            "missions, and coordinate the existing planning, engineering, repository, release, deployment, and "
            "verification capabilities. Consequential actions still require the applicable founder and governance approvals. "
            "Capabilities without current evidence remain unverified."
        )

    @staticmethod
    def _capability_comparison(message: str) -> str:
        requested = [
            name
            for name, pattern in (
                ("Jarvis", r"\bjarvis\b|\byour intelligence\b"),
                ("OpenAI", r"\bopenai\b"),
                ("Claude AI", r"\bclaude(?: ai)?\b"),
                ("Gemini AI", r"\bgemini(?: ai)?\b"),
                ("Lovable", r"\blovable\b"),
                ("Replit", r"\breplit\b"),
                ("Codex", r"\bcodex\b"),
            )
            if re.search(pattern, message, flags=re.IGNORECASE)
        ]
        rows = {
            "Jarvis": ("Executive orchestration and governed delivery", "Founder decisions through verified delivery", "No independent intelligence benchmark is available"),
            "OpenAI": ("General-purpose model and tool ecosystem", "Broad reasoning and generation", "Performance varies by model and configuration"),
            "Claude AI": ("Long-context analysis and writing", "Document-heavy reasoning and synthesis", "Current performance was not measured here"),
            "Gemini AI": ("Multimodal reasoning and Google integration", "Google-centered workflows", "Current performance was not measured here"),
            "Lovable": ("Rapid application generation", "Fast product prototyping", "Different focus from governed company operations"),
            "Replit": ("Integrated cloud development workspace", "Interactive coding and hosting", "Different focus from executive orchestration"),
            "Codex": ("Software engineering and repository work", "Implementation, review, and coding workflows", "Authority still depends on its operating environment"),
        }
        if not requested:
            requested = list(rows)
        table = [
            "| System | Primary strength | Best suited for | Limitation / uncertainty |",
            "|---|---|---|---|",
        ]
        table.extend(
            "| %s | %s | %s | %s |" % ((name,) + rows[name])
            for name in requested
        )
        return (
            "There is no defensible single intelligence grade across these systems because they optimize for different jobs. "
            "This is a capability comparison, not an independent benchmark.\n\n"
            + "\n".join(table)
            + "\n\nJarvis is strongest as the governed executive interface to AI Software Factory, while the others "
            "have different strengths. I cannot verify current model-to-model quality from repository evidence alone."
        )

    @staticmethod
    def _status(context: Dict[str, Any]) -> str:
        observations = context.get("observations") or {}
        if not observations:
            return "Current status evidence is unavailable. I will not substitute an older mission or inferred state."
        return (
            "Current verified status: %s active mission(s), %s blocked mission(s). "
            "Any field without current durable evidence remains unknown."
            % (
                observations.get("active_missions", 0),
                observations.get("blocked_missions", 0),
            )
        )

    @staticmethod
    def _already_told_governed_mission_pending(history: List[Dict[str, Any]]) -> bool:
        # Role naming isn't consistent across callers (JS sends "founder"/"jarvis"; other
        # harnesses use "user"/"board"), so this checks message text rather than role -
        # "governed mission" is Jarvis's own fallback phrasing, not something a founder
        # would type back, so a plain text scan is a safe way to detect "I already said this".
        return any(
            "governed mission" in str(item.get("text") or "").lower()
            for item in history
        )

    @staticmethod
    def _redact(text: str) -> str:
        if any(pattern in text.lower() for pattern in _INTERNAL_PATTERNS):
            return "I could not safely present the draft because it contained internal operating data. No action has been taken."
        return text

    @staticmethod
    def _artifacts(text: str, contract: ConversationContract, founder_message: str) -> Dict[str, List[Dict[str, Any]]]:
        decisions: List[Dict[str, Any]] = []
        actions: List[Dict[str, Any]] = []
        proposals: List[Dict[str, Any]] = []
        if "DECISION" in contract.permissible_artifacts:
            first = text.split("\n\n", 1)[0].strip()
            decisions.append({
                "type": "DECISION",
                "state": "proposed",
                "statement": first,
                "rationale": "Founder review is required before treating this recommendation as accepted.",
                "confidence": "medium",
                "assumptions": ["Recommendation is based on the information currently available in the conversation."],
            })
        if "ACTION" in contract.permissible_artifacts:
            next_text = next(
                (paragraph for paragraph in text.split("\n\n") if paragraph.lower().startswith(("next", "start", "first"))),
                "Review the recommendation and decide whether to continue.",
            )
            actions.append({
                "type": "ACTION",
                "state": "proposed",
                "action": next_text,
                "owner": "Jarvis",
                "approval_required": False,
            })
        if "MISSION_PROPOSAL" in contract.permissible_artifacts and contract.mode in {"EXECUTION_REQUEST", "PROJECT_PLANNING"}:
            # The real founder message, not contract.requested_outcome (a generic,
            # hardcoded per-family label like "Prepare or perform a consequential
            # action under governance" - founder_conversation_contract.py's classify()
            # never passes a real outcome, so requested_outcome is always this fixed
            # string). A real, reproduced production bug: this generic label was
            # carried unchanged as the mission's actual objective all the way through
            # founder_decision/builder.py -> action_service.py -> execution/
            # orchestrator.py -> planning/service.py's _affected_files(), where it
            # matched no real-file keyword and produced a placeholder "path"
            # ("To be determined by repository inspection before execution.") that
            # change_set_service.py then correctly rejected - surfacing as a blocked
            # mission with the confusing "Invalid repository path: To be determined
            # by repository inspection before execution." message.
            proposals.append({
                "type": "MISSION_PROPOSAL",
                "state": "proposed",
                "objective": founder_message.strip() or contract.requested_outcome,
                "expected_output": "A founder-reviewed scope and validation plan.",
                "scope": "Planning only until explicit founder approval.",
                "approval_state": "not_approved",
            })
        return {"decisions": decisions, "actions": actions, "mission_proposals": proposals, "knowledge": []}
