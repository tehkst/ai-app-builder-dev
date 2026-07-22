from __future__ import annotations

import re
from typing import Any


SPEECH_ACTS = {
    "ANALYZE",
    "COMPARE",
    "DIAGNOSE",
    "RECOMMEND",
    "PLAN",
    "IMPLEMENT",
    "GOVERNED_ACTION",
    "QUESTION",
}
DOMINANT_GOALS = {
    "discuss",
    "analyze_existing",
    "compare_options",
    "create_new_mission",
    "continue_existing_mission",
    "execute_repository_change",
    "merge_pull_request",
    "deploy_production",
    "rollback_production",
    "inspect_mission_journey",
    "clarify",
}
EXECUTION_TERMS = {"implement", "build", "fix", "add", "create", "execute", "generate"}
GOVERNED_TERMS = {"deploy", "deployment", "merge", "rollback", "roll back", "traffic"}
WORKFLOW_STAGES = (
    "founder request",
    "executive recommendation",
    "founder approval",
    "mission creation",
    "planning",
    "engineering execution",
    "code changes",
    "pull request",
    "merge approval",
    "merge",
    "deployment approval",
    "production deployment",
    "verification",
    "mission completion",
)
NEGATIVE_PATTERNS = (
    r"\bdo not\s+(?:implement|execute|deploy|merge|roll back|rollback|create)\b[^.\n]*",
    r"\bdon't\s+(?:implement|execute|deploy|merge|roll back|rollback|create)\b[^.\n]*",
    r"\banalysis only\b[^.\n]*",
    r"\bbefore implementing anything\b[^,.\n]*",
    r"\bnot implement anything yet\b[^.\n]*",
    r"\bnot execute anything yet\b[^.\n]*",
    r"\bdo not create a mission yet\b[^.\n]*",
    r"\bstop before\s+(?:repository\s+)?execution\b[^.\n]*",
)


class RequestDecomposer:
    """Separates requested intent from operational concepts mentioned as context."""

    def decompose(self, founder_request: str) -> dict[str, Any]:
        request = founder_request.strip()
        normalized = " ".join(request.lower().split())
        constraints = self._constraints(request)
        questions = self._questions(request)
        referenced_systems = [
            stage
            for stage in WORKFLOW_STAGES
            if re.search(rf"\b{re.escape(stage)}\b", normalized)
        ]
        blocked_execution = self._blocks_execution(constraints)
        blocked_governed = self._blocks_governed_action(constraints)
        direct_governed = self._direct_governed_action(request)
        direct_implementation = self._direct_implementation(request)
        dominant_goal = self._dominant_goal(
            request,
            constraints=constraints,
            questions=questions,
            direct_governed=direct_governed,
            direct_implementation=direct_implementation,
        )
        requested_action = self._speech_act(
            request,
            questions,
            dominant_goal=dominant_goal,
            direct_implementation=direct_implementation,
            direct_governed=direct_governed,
            blocked_execution=blocked_execution,
            blocked_governed=blocked_governed,
        )
        execution_requested = requested_action in {"IMPLEMENT", "GOVERNED_ACTION"} and not blocked_execution
        governed_requested = requested_action == "GOVERNED_ACTION" and not blocked_governed
        intent_type = (
            "informational_capability_query"
            if requested_action in {"QUESTION", "ANALYZE"} and self._is_informational_capability_query(request)
            else requested_action.lower()
        )
        return {
            "primary_objective": self._objective(request, requested_action, referenced_systems),
            "requested_action": requested_action,
            "explicit_constraints": constraints,
            "questions_to_answer": questions,
            "referenced_systems": referenced_systems,
            "execution_requested": execution_requested,
            "governed_action_requested": governed_requested,
            "dominant_goal": dominant_goal,
            "lifecycle_context": self._lifecycle_context(dominant_goal),
            "mission_creation_requested": dominant_goal == "create_new_mission",
            "repository_execution_requested": dominant_goal == "execute_repository_change" and not blocked_execution,
            "intent_type": intent_type,
        }

    @staticmethod
    def _is_informational_capability_query(request: str) -> bool:
        normalized = " ".join(request.lower().split())
        capability_subject = bool(re.search(
            r"\b(?:capabilit(?:y|ies)|limitations?|workflows?|missions?|execution|what\s+(?:can|are)\s+you|what\s+you\s+are|what\s+you\s+can|perform|do\s+on\s+your\s+own)\b",
            normalized,
        ))
        information_request = bool(re.search(
            r"^(?:jarvis\s+)?(?:tell|explain|list|describe|show|what|which|how)\b|\b(?:tell me|explain|list)\b",
            normalized,
        ))
        direct_action = RequestDecomposer._direct_governed_action(request) or RequestDecomposer._direct_implementation(request)
        return capability_subject and information_request and not direct_action

    @staticmethod
    def _constraints(request: str) -> list[str]:
        constraints: list[str] = []
        for pattern in NEGATIVE_PATTERNS:
            for match in re.finditer(pattern, request, flags=re.IGNORECASE):
                value = " ".join(match.group(0).strip().split())
                normalized = value[0].upper() + value[1:] if value else ""
                lowered = normalized.lower()
                if normalized and not any(
                    lowered in existing.lower() or existing.lower() in lowered
                    for existing in constraints
                ):
                    constraints.append(normalized)
        for line in request.splitlines():
            value = line.strip().rstrip(".")
            if value.lower().startswith(("prefer ", "do not assume ", "without ")):
                normalized = value[0].upper() + value[1:] + "."
                if normalized not in constraints:
                    constraints.append(normalized)
        return constraints

    @staticmethod
    def _questions(request: str) -> list[str]:
        questions: list[str] = []
        for line in request.splitlines():
            value = line.strip()
            numbered = re.match(r"^\d+[.)]\s*(.+)", value)
            if numbered:
                question = numbered.group(1).strip().rstrip(".")
                questions.append(question)
            elif value.endswith("?"):
                questions.append(value.rstrip("?"))
        if questions:
            return questions
        for sentence in re.split(r"(?<=[?.!])\s+", request):
            value = sentence.strip()
            if value.endswith("?"):
                questions.append(value.rstrip("?"))
        return questions

    def _speech_act(
        self,
        request: str,
        questions: list[str],
        *,
        dominant_goal: str,
        direct_implementation: bool,
        direct_governed: bool,
        blocked_execution: bool,
        blocked_governed: bool,
    ) -> str:
        normalized = " ".join(request.lower().split())
        analytical = bool(re.search(r"\b(analy[sz]e|inspect|assess|review|evaluate|explain)\b", normalized))
        diagnostic = bool(re.search(r"\b(gap analysis|gaps?|breaks?|root causes?|why|manual work|preventing)\b", normalized))
        recommendation = bool(re.search(r"\b(recommend|what should|highest[- ]leverage|biggest improvement)\b", normalized))
        planning = bool(
            re.search(r"\b(plan|roadmap|strategy)\b", normalized)
            and re.search(r"\b(create|build|prepare|give me|plan)\b", normalized)
        )
        critique = bool(re.search(r"\b(critique|challenge)\b", normalized))
        pruning = bool(re.search(r"\b(stop|cut)\b", normalized))
        comparison = self._has_explicit_comparison(request)

        if dominant_goal == "create_new_mission":
            return "IMPLEMENT"
        if dominant_goal in {"merge_pull_request", "deploy_production", "rollback_production"} and not blocked_governed:
            return "GOVERNED_ACTION"
        if dominant_goal == "execute_repository_change" and not blocked_execution:
            return "IMPLEMENT"
        if dominant_goal == "compare_options":
            return "COMPARE"
        if dominant_goal == "inspect_mission_journey":
            return "DIAGNOSE" if diagnostic else "ANALYZE"
        if blocked_execution and (analytical or diagnostic):
            return "DIAGNOSE" if diagnostic else "ANALYZE"
        if direct_governed and not blocked_governed:
            return "GOVERNED_ACTION"
        if direct_implementation and not blocked_execution and not planning:
            return "IMPLEMENT"
        if diagnostic:
            return "DIAGNOSE"
        if comparison:
            return "COMPARE"
        if planning:
            return "PLAN"
        if critique or pruning:
            return "RECOMMEND"
        if recommendation:
            return "RECOMMEND"
        if analytical:
            return "ANALYZE"
        if questions or request.rstrip().endswith("?"):
            return "QUESTION"
        return "QUESTION"

    @staticmethod
    def _dominant_goal(
        request: str,
        *,
        constraints: list[str],
        questions: list[str],
        direct_governed: bool,
        direct_implementation: bool,
    ) -> str:
        normalized = " ".join(request.lower().split())
        constraint_text = " ".join(constraints).lower()
        blocks_execution = RequestDecomposer._blocks_execution(constraints)
        blocks_governed = RequestDecomposer._blocks_governed_action(constraints)

        if direct_governed and not blocks_governed:
            if re.match(r"^(?:please\s+)?merge\b", RequestDecomposer._action_clause(request), re.IGNORECASE):
                return "merge_pull_request"
            if re.match(r"^(?:please\s+)?(?:roll\s+back|rollback)\b", RequestDecomposer._action_clause(request), re.IGNORECASE):
                return "rollback_production"
            return "deploy_production"

        creates_mission = bool(
            re.search(r"\b(?:create|start|launch|open)\b[^.\n]{0,80}\b(?:focused\s+|implementation\s+|engineering\s+)?mission\b", normalized)
        )
        prepares_mission = bool(
            re.search(r"\b(?:prepare|produce|generate)\b[^.\n]{0,80}\b(?:plan|handoff|change set|scope)\b", normalized)
        )
        if creates_mission or ("mission" in normalized and prepares_mission and "i want" in normalized):
            return "create_new_mission"

        continuation = bool(
            re.search(r"\b(?:continue|resume|advance|proceed with)\b[^.\n]{0,80}\b(?:mission|plan|work)\b", normalized)
        )
        if continuation:
            return "continue_existing_mission"

        journey_reference = (
            "journey" in normalized
            or sum(stage in normalized for stage in WORKFLOW_STAGES) >= 3
            or bool(re.search(r"\b(?:EXEC|MISSION)-[A-Z0-9-]+\b", request, flags=re.IGNORECASE))
        )
        inspection = bool(re.search(r"\b(?:inspect|trace|audit|analy[sz]e|diagnose|gaps?|breaks?)\b", normalized))
        if journey_reference and inspection:
            return "inspect_mission_journey"

        if RequestDecomposer._has_explicit_comparison(request):
            return "compare_options"
        planning_outcome = bool(
            re.search(r"\b(?:roadmap|strategy|plan|planning horizon|\d+[- ]day)\b", normalized)
            and re.search(r"\b(?:build|create|prepare|develop|give me|plan)\b", normalized)
        )
        if planning_outcome:
            return "analyze_existing"
        if direct_implementation and not blocks_execution:
            return "execute_repository_change"
        if inspection or questions or any(term in normalized for term in ("recommend", "what should", "plan", "roadmap", "critique")):
            return "analyze_existing"
        if constraint_text and blocks_execution:
            return "analyze_existing"
        if re.search(r"\b(?:it|this|that)\b", normalized) and re.search(r"\b(?:better|improve|fix|change)\b", normalized):
            return "clarify"
        if len(normalized.split()) <= 3:
            return "discuss"
        return "clarify"

    @staticmethod
    def _lifecycle_context(dominant_goal: str) -> str:
        if dominant_goal == "create_new_mission":
            return "new_mission"
        if dominant_goal == "continue_existing_mission":
            return "mission_continuation"
        if dominant_goal == "inspect_mission_journey":
            return "existing_mission_inspection"
        if dominant_goal in {
            "execute_repository_change",
            "merge_pull_request",
            "deploy_production",
            "rollback_production",
        }:
            return "governed_execution"
        if dominant_goal == "discuss":
            return "conversation"
        return "decision_support"

    @staticmethod
    def _direct_governed_action(request: str) -> bool:
        prose = RequestDecomposer._action_clause(request)
        return bool(
            re.match(
                r"^(?:please\s+)?(?:deploy|merge|roll\s+back|rollback|shift\s+traffic)\b",
                prose,
                flags=re.IGNORECASE,
            )
        )

    @staticmethod
    def _direct_implementation(request: str) -> bool:
        prose = RequestDecomposer._action_clause(request)
        return bool(
            re.match(
                r"^(?:please\s+)?(?:implement|build|fix|add|create|generate|execute|proceed)\b",
                prose,
                flags=re.IGNORECASE,
            )
        )

    @staticmethod
    def _action_clause(request: str) -> str:
        lines = [
            line.strip()
            for line in request.splitlines()
            if line.strip() and not re.match(r"^\d+[.)]", line.strip()) and "→" not in line
        ]
        return lines[0] if lines else request.strip()

    @staticmethod
    def _has_explicit_comparison(request: str) -> bool:
        first_paragraph = request.split("\n\n", 1)[0]
        return bool(
            re.search(r"\bshould\s+(?:we|i)\b[^?\n]+\b(?:or|versus|vs\.?)\b", first_paragraph, flags=re.IGNORECASE)
            or re.search(r"\bcompare\b", first_paragraph, flags=re.IGNORECASE)
        )

    @staticmethod
    def _blocks_execution(constraints: list[str]) -> bool:
        text = " ".join(constraints).lower()
        return bool(re.search(r"do not|don't|analysis only|before implementing|not implement|not execute|stop before.*execution", text))

    @staticmethod
    def _blocks_governed_action(constraints: list[str]) -> bool:
        text = " ".join(constraints).lower()
        return bool(re.search(r"do not (?:deploy|merge|roll back|rollback|execute)|don't (?:deploy|merge|roll back|rollback|execute)", text))

    @staticmethod
    def _objective(request: str, requested_action: str, systems: list[str]) -> str:
        first_sentence = re.split(r"(?<=[.!?])\s+", request.strip(), maxsplit=1)[0]
        target = re.sub(r"^i want\s+", "", first_sentence, flags=re.IGNORECASE).rstrip(".")
        if requested_action == "DIAGNOSE":
            if systems:
                return "Identify the smallest gaps preventing the referenced end-to-end journey from completing successfully"
            subject = re.sub(
                r"^why\s+(?:do|does|are|is)\s+",
                "",
                target,
                flags=re.IGNORECASE,
            ).rstrip("?")
            return f"Identify why {subject}"
        if requested_action == "ANALYZE":
            return f"Assess {target}"
        if requested_action == "COMPARE":
            return f"Compare the explicit alternatives in: {target}"
        if requested_action == "PLAN":
            return f"Prepare a decision-ready plan for {target}"
        if requested_action == "IMPLEMENT":
            cleaned_target = re.sub(
                r"^(?:implement|build|fix|add|create)\s+",
                "",
                target,
                flags=re.IGNORECASE,
                )
            cleaned_target = re.sub(
                r"^AI Software Factory\s+to\s+",
                "",
                cleaned_target,
                flags=re.IGNORECASE,
            )
            if re.match(r"^(?:modify|improve|update|change|prepare)\b", cleaned_target, flags=re.IGNORECASE):
                return cleaned_target[0].upper() + cleaned_target[1:]
            return f"Deliver {cleaned_target}"
        if requested_action == "GOVERNED_ACTION":
            return target[0].upper() + target[1:] if target else "Complete the requested governed action"
        if requested_action == "RECOMMEND":
            return f"Recommend the highest-value next step for {target}"
        return f"Answer the founder's question about {target}"
