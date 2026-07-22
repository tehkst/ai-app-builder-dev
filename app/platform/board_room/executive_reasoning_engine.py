from __future__ import annotations

import json
import re
from typing import Any

from app.platform.board_room.context_retriever import ContextRetriever
from app.platform.board_room.execution_first_policy import ExecutionFirstPolicy
from app.platform.board_room.recommendation_generator import RecommendationGenerator
from app.platform.board_room.request_decomposer import RequestDecomposer
from app.platform.board_room.response_presenter import ResponsePresenter


class ExecutiveReasoningEngine:
    """Runs the read-only executive reasoning pipeline before Board Room action."""

    def __init__(self) -> None:
        self.context_retriever = ContextRetriever()
        self.recommendation_generator = RecommendationGenerator()
        self.response_presenter = ResponsePresenter()

    def reason(
        self,
        founder_request: str,
        *,
        response_mode: str,
        decomposition: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        lightweight = response_mode == "casual"
        decomposition = decomposition or RequestDecomposer().decompose(founder_request)
        if decomposition.get("intent_type") == "informational_capability_query":
            return self._capability_answer(decomposition)
        context = self.context_retriever.retrieve(
            founder_request,
            lightweight=lightweight,
            decomposition=decomposition,
        )

        # CORE-001: approved execution commands route before diagnostic or
        # recommendation handling. This class stays read-only and delegates actual
        # state mutation to the existing mission pipeline.
        if ExecutionFirstPolicy.should_execute(founder_request, context, decomposition):
            return ExecutionFirstPolicy.handoff(founder_request, context, decomposition)
        if (
            ExecutionFirstPolicy.is_execution_instruction(founder_request)
            and decomposition.get("dominant_goal") == "continue_existing_mission"
        ):
            return ExecutionFirstPolicy.missing_durable_context(decomposition, context)

        # MC-JARVIS-02: evidence retrieval is an explicit read intent, not a
        # recommendation opportunity. Reuse the context sources already hydrated
        # above; do not create another evidence store, registry, or retrieval service.
        if self._is_diagnostic_evidence_request(founder_request):
            evidence = self._diagnostic_evidence(founder_request, context)
            return {
                "reasoning": {
                    "intent": "diagnostic_evidence_retrieval",
                    "request_decomposition": {
                        **decomposition,
                        "dominant_goal": "inspect_mission_journey",
                    },
                    "presentation_mode": "diagnostic_evidence",
                    "diagnostic_evidence": evidence,
                    "technical_details": {
                        "diagnostic_evidence": evidence,
                        "routing": "evidence-before-recommendation",
                    },
                },
                "founder_response": self._present_diagnostic_evidence(evidence),
                "context": context,
                "technical_details": {
                    "diagnostic_evidence": evidence,
                    "routing": "evidence-before-recommendation",
                },
            }

        reasoning = self.recommendation_generator.generate(
            founder_request,
            context,
            response_mode=response_mode,
            decomposition=decomposition,
        )
        self._enforce_context_continuity(reasoning, context, response_mode=response_mode)
        return {
            "reasoning": reasoning,
            "founder_response": self.response_presenter.present(reasoning),
            "context": context,
            "technical_details": reasoning.get("technical_details") or {},
        }

    @staticmethod
    def _capability_answer(decomposition: dict[str, Any]) -> dict[str, Any]:
        objective = str(decomposition.get("primary_objective") or "").lower()
        if "not do" in objective or "cannot" in objective:
            response = "\n".join([
                "I cannot act outside the governance that protects the company:",
                "",
                "- I cannot approve my own governed actions or bypass founder approval.",
                "- I cannot bypass security, release gates, or execution policy.",
                "- I cannot claim a branch, pull request, merge, deployment, verification, or rollback completed without durable evidence.",
                "- I cannot continue a mission when its durable mission and workflow identity are unavailable.",
                "- I cannot expose secrets or treat capability as authority.",
                "",
                "When a required approval, service, or runtime dependency is unavailable, I will explain the blocker and the safest next step.",
            ])
        else:
            response = "\n".join([
                "I can carry a governed software mission across these stages:",
                "",
                "- Clarify the objective, assess options, and prepare a decision-ready mission.",
                "- Inspect repository structure, architecture, platform health, and existing capabilities.",
                "- Produce engineering plans, validation plans, and reviewable code-change proposals.",
                "- Coordinate specialist agents and durable mission workflow runs.",
                "- Create feature branches, commits, pushes, and pull requests after authorization.",
                "- Inspect CI and pull-request readiness, then merge only with the required approval.",
                "- Deploy, verify production, and roll back through their separate approval gates.",
                "",
                "My limits are deliberate: I cannot bypass founder approval, governance, security, release gates, or unavailable runtime configuration. I will explain what is blocked rather than claim an action completed.",
            ])
        reasoning = {
            "intent": "informational_capability_query",
            "presentation_mode": "capability_summary",
            "request_decomposition": decomposition,
            "governance": {"read_only": True, "execution_requested": False},
        }
        return {"reasoning": reasoning, "founder_response": response, "context": {"sources": {}}, "technical_details": {}}

    @staticmethod
    def _is_diagnostic_evidence_request(founder_request: str) -> bool:
        normalized = " ".join(founder_request.lower().split())
        retrieval = bool(
            re.search(
                r"\b(show|present|display|retrieve|surface|inspect|provide|give me|expose)\b",
                normalized,
            )
        )
        evidence_subject = bool(
            re.search(
                r"\b(evidence|artifact|report|failure|error|blocker|runtime|validation|log|trace|broken read path)\b",
                normalized,
            )
        )
        return retrieval and evidence_subject

    @classmethod
    def _diagnostic_evidence(
        cls,
        founder_request: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        continuity = context.get("executive_continuity") or {}
        mission_match = re.search(r"\bMISSION-[A-Z0-9-]+\b", founder_request, flags=re.IGNORECASE)
        mission_id = (
            mission_match.group(0).upper()
            if mission_match
            else str(continuity.get("mission_id") or "").strip() or None
        )
        workflow_run_id = str(continuity.get("workflow_run_id") or "").strip() or None
        sources = context.get("sources") or {}
        inspected: list[dict[str, Any]] = []
        artifacts: list[dict[str, Any]] = []

        for source_name in (
            "mission_history",
            "journey_inspection",
            "executive_intelligence",
            "repository_intelligence",
            "engineering_capacity",
        ):
            payload = sources.get(source_name)
            if payload is None and source_name == "journey_inspection":
                payload = context.get("journey_evidence")
            if not isinstance(payload, dict):
                inspected.append({"source": source_name, "status": "unavailable"})
                continue
            status = str(payload.get("status") or "available")
            inspected.append({"source": source_name, "status": status})
            cls._collect_relevant_artifacts(
                payload,
                source_name=source_name,
                mission_id=mission_id,
                artifacts=artifacts,
            )

        unique: list[dict[str, Any]] = []
        seen: set[str] = set()
        for artifact in artifacts:
            key = json.dumps(artifact.get("evidence"), sort_keys=True, default=str)
            if key in seen:
                continue
            seen.add(key)
            unique.append(artifact)

        detailed = any(
            any(
                token in json.dumps(item.get("evidence"), default=str).lower()
                for token in ("validation", "failure", "error", "detail", "blocked")
            )
            for item in unique
        )
        evidence_status = "found" if detailed else ("partial" if unique else "unavailable")
        missing = []
        if evidence_status != "found":
            missing.append(
                "The retrieved read models do not expose the complete underlying validation artifact or raw runtime report."
            )
        if not workflow_run_id:
            missing.append("No workflow_run_id was resolved from the retrieved executive context.")

        return {
            "intent": "diagnostic_evidence_retrieval",
            "mission_id": mission_id,
            "workflow_run_id": workflow_run_id,
            "evidence_status": evidence_status,
            "sources_inspected": inspected,
            "artifacts": unique[:12],
            "missing_evidence": missing,
            "supported_conclusion": cls._supported_conclusion(evidence_status, mission_id, unique),
            "governance": {
                "read_only": True,
                "stores_state": False,
                "creates_new_retrieval_system": False,
                "recommendation_ranking_bypassed": True,
            },
        }

    @classmethod
    def _collect_relevant_artifacts(
        cls,
        value: Any,
        *,
        source_name: str,
        mission_id: str | None,
        artifacts: list[dict[str, Any]],
        path: str = "$",
        depth: int = 0,
    ) -> None:
        if depth > 8 or len(artifacts) >= 24:
            return
        if isinstance(value, dict):
            serialized = json.dumps(value, default=str).lower()
            mission_matches = not mission_id or mission_id.lower() in serialized
            evidence_keys = {
                "blocking_reason",
                "blocked_reason",
                "blocker",
                "error",
                "error_classification",
                "failure",
                "failure_detail",
                "detail",
                "validation",
                "validation_result",
                "change_set_validation_failure",
                "first_broken_or_manual_transition",
            }
            relevant_keys = evidence_keys.intersection(value.keys())
            if mission_matches and relevant_keys:
                evidence = {
                    key: value.get(key)
                    for key in sorted(relevant_keys)
                    if value.get(key) not in (None, "", [], {})
                }
                if evidence:
                    artifacts.append(
                        {
                            "source": source_name,
                            "source_path": path,
                            "evidence": evidence,
                        }
                    )
            for key, nested in value.items():
                cls._collect_relevant_artifacts(
                    nested,
                    source_name=source_name,
                    mission_id=mission_id,
                    artifacts=artifacts,
                    path=f"{path}.{key}",
                    depth=depth + 1,
                )
        elif isinstance(value, list):
            for index, nested in enumerate(value):
                cls._collect_relevant_artifacts(
                    nested,
                    source_name=source_name,
                    mission_id=mission_id,
                    artifacts=artifacts,
                    path=f"{path}[{index}]",
                    depth=depth + 1,
                )

    @staticmethod
    def _supported_conclusion(
        evidence_status: str,
        mission_id: str | None,
        artifacts: list[dict[str, Any]],
    ) -> str:
        subject = f"Mission {mission_id}" if mission_id else "The referenced mission"
        if evidence_status == "found":
            return f"{subject} has diagnostic evidence in the existing read models; only the surfaced artifacts are supported."
        if artifacts:
            return f"{subject} is visible, but only summary evidence is exposed; the exact underlying runtime artifact is not available through the current read models."
        return f"No diagnostic artifact for {subject.lower()} was found in the existing read models."

    @staticmethod
    def _present_diagnostic_evidence(evidence: dict[str, Any]) -> str:
        lines = [
            "Diagnostic evidence retrieval",
            f"Mission: {evidence.get('mission_id') or 'unresolved'}",
            f"Workflow run: {evidence.get('workflow_run_id') or 'unresolved'}",
            f"Evidence status: {str(evidence.get('evidence_status') or 'unavailable').upper()}",
            "",
            "Sources inspected:",
        ]
        for source in evidence.get("sources_inspected") or []:
            lines.append(f"- {source.get('source')}: {source.get('status')}")
        artifacts = evidence.get("artifacts") or []
        lines.extend(["", "Evidence found:"])
        if artifacts:
            for artifact in artifacts:
                rendered = json.dumps(artifact.get("evidence"), default=str, ensure_ascii=False)
                lines.append(f"- {artifact.get('source')} {artifact.get('source_path')}: {rendered}")
        else:
            lines.append("- No matching diagnostic artifact was exposed by the retrieved sources.")
        missing = evidence.get("missing_evidence") or []
        if missing:
            lines.extend(["", "Missing evidence:"])
            lines.extend(f"- {item}" for item in missing)
        lines.extend(["", f"Supported conclusion: {evidence.get('supported_conclusion')}"])
        return "\n".join(lines)

    @staticmethod
    def _enforce_context_continuity(
        reasoning: dict[str, Any],
        context: dict[str, Any],
        *,
        response_mode: str,
    ) -> None:
        """Prevent a silent return to generic clarification when context exists."""

        continuity = context.get("executive_continuity") or {}
        if response_mode != "clarify" or not continuity.get("has_context"):
            return

        decomposition = dict(reasoning.get("request_decomposition") or {})
        decomposition["dominant_goal"] = "analyze_existing"
        decomposition["lifecycle_context"] = str(
            continuity.get("lifecycle_context") or "mission_continuation"
        )
        reasoning["request_decomposition"] = decomposition
        reasoning["presentation_mode"] = "diagnosis"

        mission_id = str(continuity.get("mission_id") or "").strip()
        blocker = str(continuity.get("blocking_reason") or "").strip()
        source_failures = continuity.get("source_failures") or []

        subject = f"mission {mission_id}" if mission_id else "the current executive context"
        if blocker:
            action = f"Continue diagnosing {subject} from its preserved blocker: {blocker}"
            why = "The request is a continuation of known executive work, so asking the founder to restate the business outcome would discard available context."
        else:
            action = f"Continue from {subject} and resolve the first missing evidence link"
            why = "Existing executive context is available and must be used before asking a generic clarification question."

        reasoning["recommendation"] = {
            "action": action,
            "why": why,
            "confidence": "high" if mission_id else "medium",
        }
        reasoning["next_action"] = (
            "Inspect the preserved mission/runtime evidence and identify the exact broken read path."
            if mission_id
            else "Use the available Executive Intelligence and mission history to continue the current investigation."
        )

        existing_evidence = list(reasoning.get("evidence") or [])
        continuity_evidence = []
        if mission_id:
            continuity_evidence.append(
                {"fact": f"Executive context references mission {mission_id}.", "source": "executive_continuity"}
            )
        if blocker:
            continuity_evidence.append(
                {"fact": f"The preserved blocking reason is {blocker}.", "source": "executive_continuity"}
            )
        if source_failures:
            continuity_evidence.append(
                {
                    "fact": "Context sources requiring attention: " + ", ".join(str(item) for item in source_failures),
                    "source": "executive_continuity",
                }
            )
        reasoning["evidence"] = continuity_evidence + existing_evidence
        reasoning.setdefault("technical_details", {})["executive_context_continuity"] = continuity

    @staticmethod
    def build_ai_guidance(result: dict[str, Any]) -> str:
        reasoning = result.get("reasoning") or {}
        recommendation = reasoning.get("recommendation") or {}
        alternatives = reasoning.get("alternatives") or []
        risk = reasoning.get("risk") or {}
        criteria = reasoning.get("evaluation_criteria") or []
        evidence = reasoning.get("evidence") or []
        uncertainty = reasoning.get("uncertainty") or []
        presentation_mode = reasoning.get("presentation_mode") or "prioritization"
        decomposition = reasoning.get("request_decomposition") or {}
        if presentation_mode == "execution_handoff":
            handoff = reasoning.get("execution_handoff") or {}
            return "\n".join(
                [
                    "Present the structured execution state directly.",
                    "Do not convert the action into a recommendation, diagnosis, or alternative analysis.",
                    "Do not ask whether to continue.",
                    f"Execution handoff: {handoff}",
                ]
            )
        if presentation_mode == "diagnostic_evidence":
            diagnostic = reasoning.get("diagnostic_evidence") or {}
            return "\n".join(
                [
                    "Present the retrieved diagnostic evidence directly.",
                    "Do not replace evidence retrieval with recommendations or ranked options.",
                    f"Diagnostic evidence: {diagnostic}",
                ]
            )
        return "\n".join(
            [
                "Lead with the recommendation and use concise business language.",
                f"Presentation mode hint: {presentation_mode}",
                f"Dominant founder goal: {decomposition.get('dominant_goal', 'decision support')}",
                f"Lifecycle context: {decomposition.get('lifecycle_context', 'unknown')}",
                f"Founder intent: {reasoning.get('intent', 'evaluate the request')}",
                f"Business context: {reasoning.get('business_context', '')}",
                f"Company memory: {reasoning.get('company_memory', '')}",
                f"Recommended action: {recommendation.get('action', '')}",
                f"Rationale: {recommendation.get('why', '')}",
                f"Alternatives: {alternatives}",
                f"Evaluation criteria: {criteria}",
                f"Observed evidence: {evidence}",
                f"Uncertainty: {uncertainty}",
                f"Risk: {risk.get('level', 'moderate')}",
                f"Decision questions: {reasoning.get('decision', {})}",
                f"Next action: {reasoning.get('next_action', '')}",
                "Write a natural executive response. Do not force headings or repeat sections that add no value.",
                "Keep implementation mechanics out of the founder-facing response.",
            ]
        )
