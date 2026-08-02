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
        executive_brief: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        decomposition: Optional[Dict[str, Any]] = None,
    ) -> FounderResponse:
        signals = cls._quality_signals(draft, founder_message, contract, decomposition)
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
        artifacts = cls._artifacts(text, contract)
        return FounderResponse(
            text=text,
            decisions=artifacts["decisions"],
            actions=artifacts["actions"],
            mission_proposals=artifacts["mission_proposals"],
            knowledge=artifacts["knowledge"],
            validation={
                "passed": not cls._quality_signals(text, founder_message, contract, decomposition),
                "initial_signals": signals,
            },
            fallback_used=fallback_used,
        )

    @classmethod
    def _quality_signals(
        cls,
        text: str,
        message: str,
        contract: ConversationContract,
        decomposition: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        lowered = text.lower().strip()
        signals = []
        if not lowered:
            signals.append("empty")
        if any(pattern in lowered for pattern in _INTERNAL_PATTERNS):
            signals.append("internal_evidence_leak")
        if text.count("{") and text.count("}") and any(term in lowered for term in ("status", "gates", "authority")):
            signals.append("raw_object")
        if contract.mode == "PRODUCT_DISCOVERY":
            for label, terms in {
                "target_user_missing": ("target", "operator", "business"),
                "scope_missing": ("mvp", "first version", "include"),
                "commercial_case_missing": ("commercial", "revenue", "pay", "valuable"),
                "next_step_missing": ("next", "interview", "discovery", "validate"),
            }.items():
                if not any(term in lowered for term in terms):
                    signals.append(label)
        # An "executive_discussion"/STRATEGIC_ADVICE-family message is not always a
        # request for a recommendation - the decomposer's requested_action distinguishes
        # "evaluate/list/map the current state" (ANALYZE) from "tell me what to do"
        # (RECOMMEND/COMPARE/PLAN). Requiring recommendation-framed language from an
        # honest evaluation/audit answer was a real, reproduced bug: it discarded a
        # correct, on-topic answer and substituted the generic canned fallback below
        # purely because the answer didn't use words like "recommend" or "should".
        requested_action = str((decomposition or {}).get("requested_action") or "")
        if contract.mode == "STRATEGIC_ADVICE" and requested_action != "ANALYZE" and not any(
            term in lowered
            for term in ("recommend", "prioriti", "my view", "choose", "focus", "suggest", "should", "next step", "advise", "start with")
        ):
            signals.append("recommendation_missing")
        if len(lowered) < 40 and len(message) > 80:
            signals.append("insubstantial")
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
            return cls._product_discovery(message, history)
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
            return cls._strategic_advice(message)
        if mode == "BRAINSTORMING":
            return (
                "I could not generate sufficiently grounded options from the available evidence. "
                "No recommendation or action has been created."
            )
        if mode == "CONVERSATIONAL_FOLLOW_UP":
            return cls._follow_up(message, history)
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
    def _product_discovery(message: str, history: List[Dict[str, Any]]) -> str:
        text = message.lower()
        history_text = " ".join(str(item.get("text") or "") for item in history).lower()
        combined = history_text + " " + text
        if "transport" in combined and "crm" in combined:
            return (
                "Start with owner-led transport operators running roughly 5–50 vehicles. They are large enough to feel the cost of "
                "spreadsheet, WhatsApp, and paper-based coordination, but usually too small for heavyweight fleet and ERP systems.\n\n"
                "The first version should be an operations-focused CRM, not a generic contact database. Include customer and contact records, "
                "quotation follow-up, job scheduling, driver and vehicle assignment, invoicing, and payment tracking. Defer telematics, route "
                "optimisation, payroll, advanced analytics, and broad accounting integrations until customers prove they matter.\n\n"
                "Commercially, the product is attractive if it connects the full path from enquiry to cash collection. That creates a measurable "
                "return through fewer missed jobs, faster administration, and quicker payment, which supports recurring subscription pricing. "
                "The core trade-off is breadth versus workflow depth: winning one daily transport workflow is more valuable than shipping a wide but shallow CRM.\n\n"
                "Next, I would prepare the operator profiles, interview guide, workflow prototype, and evidence scorecard. "
                "Confirm the target customer assumption, and I will prepare a bounded discovery mission for your review."
            )
        if "school" in combined and "management" in combined:
            return (
                "Before building, choose the first buyer and operating problem. My working assumption would be a small private school whose administrator "
                "needs admissions, student records, attendance, fee tracking, and parent communication in one place. Avoid timetabling, payroll, learning "
                "management, and government reporting in the first release unless interviews make one of them essential.\n\n"
                "My working assumption is the school administrator. The one material choice is whether the first user should instead be the owner or teacher. "
                "Which country's fee and reporting rules apply remains a later localisation assumption rather than a reason to block useful discovery. "
                "Once you choose the first user, I would prepare the school profiles, discovery guide, workflow prototype, and evidence scorecard for your review."
            )
        return (
            "My recommendation is to start with a small service business and one frequent enquiry-to-payment workflow as the working assumption. "
            "I would prepare the customer profile, validation questions, workflow prototype, and evidence scorecard. "
            "You only need to confirm or change that target before approving a bounded discovery mission."
        )

    @staticmethod
    def _strategic_advice(message: str) -> str:
        text = message.lower()
        if all(term in text for term in ("jarvis", "ui", "code generation")):
            return (
                "Prioritize Jarvis intelligence first, then strengthen code generation, then improve the UI around proven workflows, and place Digital Twin testing after "
                "the execution path is producing dependable artifacts. Better executive decisions improve every downstream investment; stronger code generation then turns "
                "those decisions into value. A UI polish pass before those two foundations would make the system look more complete without making it materially more capable."
            )
        if "lovable" in text or "replit" in text or "software agency" in text:
            return (
                "AI Software Factory should not compete as the fastest one-screen app generator. Its differentiated promise is a governed company operating loop: executive "
                "reasoning, durable missions, engineering execution, repository and PR controls, deployment, and verification with founder approval at consequential boundaries. "
                "Lovable and Replit are generally stronger for rapid interactive building, while an agency provides human accountability and bespoke delivery. Today, AI Software "
                "Factory's weakness is product coherence and proven end-to-end reliability. The credible strategy is to win on traceable, governed delivery, then prove it with a small number of complete founder missions."
            )
        return (
            "My recommendation is to choose the option that produces the strongest customer evidence with the least irreversible investment. "
            "Run one bounded proof, define the decision it must unlock, and defer parallel work until that evidence is available."
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
    def _follow_up(message: str, history: List[Dict[str, Any]]) -> str:
        previous = " ".join(str(item.get("text") or "") for item in history).lower()
        if "transport" in previous and ("50 vehicles" in previous or "fewer than 50" in previous):
            return (
                "For transport companies with fewer than 50 vehicles, build the enquiry-to-payment workflow first: customer records, quotes, job scheduling, "
                "driver and vehicle assignment, invoicing, and payment tracking. That gives the operator one daily operating view without the cost of a full fleet system."
            )
        return "Continue with the smallest step that tests the assumption established earlier in this conversation; no execution has started."

    @staticmethod
    def _redact(text: str) -> str:
        if any(pattern in text.lower() for pattern in _INTERNAL_PATTERNS):
            return "I could not safely present the draft because it contained internal operating data. No action has been taken."
        return text

    @staticmethod
    def _artifacts(text: str, contract: ConversationContract) -> Dict[str, List[Dict[str, Any]]]:
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
            proposals.append({
                "type": "MISSION_PROPOSAL",
                "state": "proposed",
                "objective": contract.requested_outcome,
                "expected_output": "A founder-reviewed scope and validation plan.",
                "scope": "Planning only until explicit founder approval.",
                "approval_state": "not_approved",
            })
        return {"decisions": decisions, "actions": actions, "mission_proposals": proposals, "knowledge": []}
