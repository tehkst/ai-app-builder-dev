from __future__ import annotations

from typing import Any


class ResponsePresenter:
    """Presents reasoning in concise founder-facing language."""

    def present(self, reasoning: dict[str, Any]) -> str:
        if reasoning.get("intent") == "casual":
            return "Good to hear from you. What would you like to work through?"
        if reasoning.get("intent") == "clarify":
            return "What business outcome would you like us to achieve?"

        mode = str(reasoning.get("presentation_mode") or "prioritization")
        presenters = {
            "comparison": self._comparison,
            "prioritization": self._prioritization,
            "diagnosis": self._diagnosis,
            "critique": self._critique,
            "roadmap": self._roadmap,
            "execution": self._execution,
            "governed_action": self._governed_action,
        }
        return presenters.get(mode, self._prioritization)(reasoning)

    def _comparison(self, reasoning: dict[str, Any]) -> str:
        recommendation = self._recommendation(reasoning)
        options = reasoning.get("alternatives") or []
        tied = len(options) >= 2 and int(options[0].get("score") or 0) == int(options[1].get("score") or 0)
        option_lines = [
            f"- {item.get('option')} ({item.get('score', 'unscored')}/100): {item.get('trade_off')}"
            for item in options
        ]
        recommendation_label = "Provisional recommendation" if tied else "Recommendation"
        winner_label = "Why there is no clear winner" if tied else "Why the winner wins"
        winner_reason = (
            f"The two leading options both score {options[0].get('score')}/100. The available evidence does not establish which creates more business value."
            if tied
            else recommendation["why"]
        )
        decision = (
            "Define one measurable success outcome for each option before approval."
            if tied
            else str(reasoning.get("next_action", ""))
        )
        return self._join(
            f"{recommendation_label}: {recommendation['action']}",
            "",
            "Option-by-option comparison:",
            *option_lines,
            "",
            f"{winner_label}: {winner_reason}",
            f"Core trade-off: {self._comparison_trade_off(options)}",
            f"Decision: {decision}",
        )

    def _prioritization(self, reasoning: dict[str, Any]) -> str:
        recommendation = self._recommendation(reasoning)
        options = reasoning.get("alternatives") or []
        ranked = [
            f"{index}. {item.get('option')} ({item.get('score', 'unscored')}/100)"
            for index, item in enumerate(options, start=1)
        ]
        criteria = ", ".join(
            str(item.get("name"))
            for item in (reasoning.get("evaluation_criteria") or [])[:3]
        )
        return self._join(
            f"Top priority: {recommendation['action']}",
            "",
            "Ranked priorities:",
            *ranked,
            "",
            f"Selection criteria: {criteria}",
            f"Why now: {recommendation['why']}",
            f"Next decision: {reasoning.get('next_action', '')}",
        )

    def _diagnosis(self, reasoning: dict[str, Any]) -> str:
        recommendation = self._recommendation(reasoning)
        evidence = reasoning.get("evidence") or []
        journey = reasoning.get("journey_evidence") or {}
        resolution = journey.get("mission_resolution") or {}
        mission_resolved = resolution.get("status") == "resolved"
        evidence_lines = [
            f"- {item.get('fact')} ({item.get('source')})"
            for item in evidence[:4]
        ] or ["- Insufficient observed evidence is available for a confident diagnosis."]
        factors = self._diagnostic_inferences(evidence) if mission_resolved or not journey else []
        unknowns = self._diagnostic_unknowns(reasoning.get("uncertainty") or [])
        if journey and not mission_resolved:
            root_cause = "Mission-specific journey diagnosis is unavailable because no canonical mission identity was resolved."
            diagnosis_fit = str(resolution.get("explanation") or "Mission context is unavailable.")
            intervention = str(journey.get("smallest_next_improvement") or "Resolve the mission identity.")
        else:
            root_cause = self._diagnostic_root_cause(evidence, recommendation["action"])
            diagnosis_fit = recommendation["why"]
            intervention = str(reasoning.get("next_action", ""))
        lines = [
            f"Likely root cause: {root_cause}",
            "",
            "Observed evidence:",
            *evidence_lines,
        ]
        if factors:
            lines.extend(["", "Inferred contributing factors:", *[f"- {factor}" for factor in factors]])
        lines.extend(["", "Unknowns:", *[f"- {item}" for item in unknowns]])
        lines.extend([
            "",
            f"Why this diagnosis fits: {diagnosis_fit}",
            f"First intervention: {intervention}",
        ])
        questions = (reasoning.get("request_decomposition") or {}).get("questions_to_answer") or []
        if questions:
            lines.extend(["", "Requested answers:"])
            for index, question in enumerate(questions, start=1):
                lines.append(f"{index}. {question}: {self._answer_question(str(question), reasoning)}")
        return self._join(*lines)

    def _critique(self, reasoning: dict[str, Any]) -> str:
        recommendation = self._recommendation(reasoning)
        options = reasoning.get("alternatives") or []
        evidence = reasoning.get("evidence") or []
        direct_problems = self._critique_problems(evidence, options)
        stop = next(
            (
                str(item.get("option"))
                for item in options
                if {"stop", "continue", "expand"} & set(str(item.get("option")).lower().split())
            ),
            str(options[-1].get("option")) if options else "Stop expanding scope without a complete outcome",
        )
        corrective_action = self._corrective_action(reasoning, stop)
        return self._join(
            "Direct critique:",
            *[f"- {problem}" for problem in direct_problems],
            "",
            f"Why it matters: {reasoning.get('consequence_of_inaction', '')}",
            f"What to stop: {self._stop_behavior(stop)}",
            f"Corrective action: {corrective_action}",
            f"Immediate decision: {self._immediate_critique_decision(reasoning)}",
        )

    def _roadmap(self, reasoning: dict[str, Any]) -> str:
        recommendation = self._recommendation(reasoning)
        options = reasoning.get("alternatives") or []
        priorities = [str(item.get("option")) for item in options]
        sequence = [
            f"{index}. {priority}"
            for index, priority in enumerate(priorities, start=1)
        ]
        return self._join(
            "Priorities:",
            *[f"- {priority}" for priority in priorities],
            "",
            "Sequence:",
            *sequence,
            "",
            f"Rationale: {recommendation['why']}",
            f"Expected outcome: {reasoning.get('impact', '')}",
            f"Start with: {recommendation['action']}",
        )

    def _execution(self, reasoning: dict[str, Any]) -> str:
        recommendation = self._recommendation(reasoning)
        risk = reasoning.get("risk") or {}
        return self._join(
            f"Recommendation: {recommendation['action']}",
            f"Scope: {reasoning.get('intent', '')}",
            f"Estimated effort: {reasoning.get('estimated_effort', '')}",
            f"Risk: {self._risk_text(risk)}",
            f"Next action: {reasoning.get('next_action', '')}",
        )

    def _governed_action(self, reasoning: dict[str, Any]) -> str:
        risk = reasoning.get("risk") or {}
        governance = reasoning.get("governance") or {}
        evidence = reasoning.get("evidence") or []
        current_state = evidence[0].get("fact") if evidence else "Current state is available for review."
        return self._join(
            f"Current state: {current_state}",
            f"Required approval: {governance.get('who', 'Founder')} approval is required for {governance.get('what', 'the proposed action')}.",
            f"Risk: {self._risk_text(risk)}",
            f"Safe next action: {reasoning.get('next_action', '')}",
        )

    @staticmethod
    def _recommendation(reasoning: dict[str, Any]) -> dict[str, str]:
        recommendation = reasoning.get("recommendation") or {}
        return {
            "action": str(recommendation.get("action") or "Review the leading option"),
            "why": str(recommendation.get("why") or "It best fits the available evidence."),
        }

    @staticmethod
    def _risk_text(risk: dict[str, Any]) -> str:
        return f"{str(risk.get('level') or 'moderate').title()}. {' '.join(risk.get('factors') or [])}"

    @staticmethod
    def _comparison_trade_off(options: list[dict[str, Any]]) -> str:
        if len(options) < 2:
            return "There is insufficient evidence to compare a recommended option with a credible alternative."
        winner, alternative = options[0], options[1]
        tied = int(winner.get("score") or 0) == int(alternative.get("score") or 0)
        if tied:
            return (
                f"Choosing {str(winner.get('option')).lower()} prioritizes "
                f"{ResponsePresenter._option_outcome(str(winner.get('option')))}, while sacrificing "
                f"{ResponsePresenter._option_outcome(str(alternative.get('option')))}; current evidence does not quantify which creates more value."
            )
        winner_scores = winner.get("criteria") or {}
        alternative_scores = alternative.get("criteria") or {}
        gains = [
            name
            for name, score in winner_scores.items()
            if int(score) > int(alternative_scores.get(name, score))
        ]
        sacrifices = [
            name
            for name, score in winner_scores.items()
            if int(score) < int(alternative_scores.get(name, score))
        ]
        gain = ", ".join(gains) if gains else "a more balanced outcome"
        if sacrifices:
            sacrifice = ", ".join(sacrifices)
        elif " and " in str(winner.get("option")).lower():
            sacrifice = "some delivery simplicity and focus"
        else:
            sacrifice = "the specialist advantage of the alternative"
        return (
            f"Choosing {str(winner.get('option')).lower()} gains {gain}, but sacrifices {sacrifice} "
            f"compared with {str(alternative.get('option')).lower()}."
        )

    @staticmethod
    def _option_outcome(option: str) -> str:
        tokens = set(option.lower().replace("-", " ").split())
        if tokens & {"onboarding", "ui", "ux", "founder", "experience"}:
            return "a more direct user experience improvement"
        if tokens & {"automation", "capability", "platform", "workflow"}:
            return "broader operational leverage"
        if tokens & {"investor", "demo", "fundraising", "growth"}:
            return "faster external proof"
        if tokens & {"debt", "reliability", "quality", "stability"}:
            return "greater operational reliability"
        return "the outcome specific to that option"

    @staticmethod
    def _evidence_values(evidence: list[dict[str, Any]]) -> dict[str, str]:
        values: dict[str, str] = {}
        for item in evidence:
            fact = str(item.get("fact") or "")
            if ":" in fact:
                key, value = fact.split(":", 1)
                values[key.strip()] = value.strip()
        return values

    def _diagnostic_inferences(self, evidence: list[dict[str, Any]]) -> list[str]:
        values = self._evidence_values(evidence)
        inferences: list[str] = []
        completion = values.get("estimated completion")
        areas = values.get("repository areas")
        blocked = values.get("blocked missions")
        engineering_mode = values.get("engineering operating mode")
        if completion and areas:
            inferences.append(
                f"Inference: {completion}% estimated completion across {areas} repository areas suggests capability breadth is ahead of end-to-end completion."
            )
        if blocked == "0":
            inferences.append(
                "Inference: no formally blocked mission is reported, so the unfinished experience is unlikely to be explained by a recorded mission blockage alone."
            )
        if engineering_mode:
            inferences.append(
                f"Inference: the {engineering_mode} operating mode may create handoff gaps between planning and completed founder outcomes."
            )
        return inferences

    def _diagnostic_root_cause(
        self,
        evidence: list[dict[str, Any]],
        fallback: str,
    ) -> str:
        first_break = next(
            (
                str(item.get("fact")).split(":", 1)[1].strip()
                for item in evidence
                if str(item.get("fact")).startswith("first journey break:")
            ),
            None,
        )
        if first_break:
            return f"The first unverified journey transition is {first_break.rstrip('.')}."
        values = self._evidence_values(evidence)
        completion = values.get("estimated completion")
        areas = values.get("repository areas")
        if completion and areas:
            return f"Capability breadth across {areas} repository areas is outpacing end-to-end journey completion, currently estimated at {completion}%."
        if completion:
            return f"End-to-end completion remains incomplete at an estimated {completion}%."
        return fallback

    @staticmethod
    def _diagnostic_unknowns(uncertainty: list[str]) -> list[str]:
        specific = [
            item
            for item in uncertainty
            if not item.startswith("No material context gap")
        ]
        if specific:
            return specific
        return [
            "Founder-journey completion rates, capability usage, and time spent between mission stages are not available in the retrieved evidence."
        ]

    def _answer_question(self, question: str, reasoning: dict[str, Any]) -> str:
        lowered = question.lower()
        evidence = reasoning.get("evidence") or []
        recommendation = self._recommendation(reasoning)
        journey = reasoning.get("journey_evidence") or {}
        resolution = journey.get("mission_resolution") or {}
        mission_resolved = resolution.get("status") == "resolved"
        stages = journey.get("stages") or []
        first_break = journey.get("first_broken_or_manual_transition") or {}
        sources = sorted(
            {
                str(item.get("source"))
                for item in evidence
                if item.get("source")
            }
        )
        if any(term in lowered for term in ("already works", "working", "exists")):
            working = [
                str(stage.get("stage_name"))
                for stage in stages
                if stage.get("status") in {"verified", "ready"}
            ]
            if working:
                prefix = (
                    "Mission-specific verified or ready stages"
                    if mission_resolved
                    else "Capability-ready stages only; no mission-specific completion is verified"
                )
                return prefix + ": " + ", ".join(working) + "."
            return (
                "Existing context and planning capabilities are available through "
                + ", ".join(sources)
                + "."
                if sources
                else "The retrieved evidence is insufficient to confirm which stages work."
            )
        if any(term in lowered for term in ("break", "manual", "gap", "blocked")):
            if journey and not mission_resolved:
                return "A mission-specific break point cannot be identified until a canonical mission identity is resolved."
            if first_break:
                return (
                    f"{first_break.get('from_stage')} → {first_break.get('to_stage')} is "
                    f"{first_break.get('status')}: {first_break.get('explanation')}"
                )
            inferences = self._diagnostic_inferences(evidence)
            return inferences[0].removeprefix("Inference: ") if inferences else "The current evidence does not identify a verified break point."
        if any(term in lowered for term in ("smallest", "biggest improvement", "milestone")):
            value = str(journey.get("smallest_next_improvement") or recommendation["action"]).rstrip(".")
            return value + "."
        if any(term in lowered for term in ("reuse", "rebuilt", "rebuild")):
            reuse = journey.get("reuse_recommendations") or []
            if reuse:
                return " ".join(str(item) for item in reuse)
            return (
                "Reuse the observed "
                + ", ".join(sources)
                + " capabilities; the evidence does not justify replacing them."
                if sources
                else "No reusable capability can be confirmed from the available evidence."
            )
        if any(term in lowered for term in ("implement first", "recommend", "first")):
            improvement = str(journey.get("smallest_next_improvement") or recommendation["action"]).rstrip(".")
            return improvement + "; keep execution separate until the analysis is accepted."
        return "The available evidence does not answer this confidently; additional operational data is required."

    def _critique_problems(
        self,
        evidence: list[dict[str, Any]],
        options: list[dict[str, Any]],
    ) -> list[str]:
        values = self._evidence_values(evidence)
        problems: list[str] = []
        completion = values.get("estimated completion")
        areas = values.get("repository areas")
        active = values.get("active missions")
        if completion:
            problems.append(f"The platform is estimated at {completion}% complete, so meaningful founder journeys remain unfinished.")
        if areas and completion:
            problems.append(f"Work spans {areas} repository areas while overall completion remains {completion}%, indicating breadth is outpacing consolidation.")
        if active:
            problems.append(f"Only {active} active mission is visible, making that mission's end-to-end outcome more important than adding parallel scope.")
        if not problems:
            problems.append("Available evidence is insufficient to support a deeper critique; founder-journey completion data is needed.")
        weakest = min(options, key=lambda item: int(item.get("score") or 0)) if options else {}
        if weakest:
            problems.append(
                f"The weakest option, {weakest.get('option')}, scores {weakest.get('score')}/100; its trade-off is that it {str(weakest.get('trade_off') or '').lower().rstrip('.')}."
            )
        return problems

    @staticmethod
    def _stop_behavior(stop: str) -> str:
        lowered = stop.strip()
        if lowered.lower().startswith("stop "):
            lowered = lowered[5:]
        lowered = lowered.replace(" until ", " before ")
        return f"Starting {lowered.lower()}."

    @staticmethod
    def _corrective_action(reasoning: dict[str, Any], stop: str) -> str:
        evidence = reasoning.get("evidence") or []
        active = next(
            (
                str(item.get("fact")).split(":", 1)[1].strip()
                for item in evidence
                if str(item.get("fact")).startswith("active missions:")
            ),
            None,
        )
        if active:
            return f"Concentrate the {active} active mission on completing one measurable founder journey before expanding scope."
        return "Select one measurable founder journey and complete it before expanding scope."

    @staticmethod
    def _immediate_critique_decision(reasoning: dict[str, Any]) -> str:
        evidence = reasoning.get("evidence") or []
        active = next(
            (
                str(item.get("fact")).split(":", 1)[1].strip()
                for item in evidence
                if str(item.get("fact")).startswith("active missions:")
            ),
            "the current",
        )
        noun = "mission" if active == "1" else "missions"
        return f"Approve a temporary scope freeze and designate the {active} active {noun} as the only priority until one founder journey is verified complete."

    @staticmethod
    def _join(*lines: str) -> str:
        return "\n".join(line for line in lines if line is not None).strip()
