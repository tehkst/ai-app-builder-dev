from __future__ import annotations

import re
from typing import Any


WORD_RE = re.compile(r"[a-z0-9][a-z0-9'-]*")
ACTION_WORDS = {
    "build",
    "fix",
    "improve",
    "invest",
    "prioritize",
    "reduce",
    "ship",
    "stop",
}
CONCEPT_WEIGHTS = {
    "capacity": {"capacity", "limited", "time", "team", "engineering", "effort"},
    "growth": {"fundraise", "fundraising", "investor", "revenue", "growth", "demo", "customer"},
    "reliability": {"debt", "quality", "reliability", "stability", "repair", "unfinished", "complete"},
    "experience": {"ui", "ux", "polish", "founder", "workflow", "experience", "usable"},
    "governance": {"production", "deploy", "merge", "rollback", "auth", "secret", "approval"},
    "coherence": {"unfinished", "capabilities", "coherent", "integrate", "fragmented", "consolidate"},
}
CRITERION_SIGNALS = {
    "time to value": {"quick", "now", "limited", "capacity", "demo", "90", "days"},
    "business impact": {"business", "customer", "revenue", "investor", "fundraising", "growth"},
    "operational reliability": {"debt", "quality", "reliability", "stability", "production", "unfinished"},
    "founder experience": {"founder", "ui", "ux", "workflow", "polish", "experience"},
    "strategic coherence": {"strategy", "priority", "stop", "capabilities", "unfinished", "coherent"},
    "execution risk": {"risk", "deploy", "production", "merge", "rollback", "auth", "secret"},
    "reversibility": {"experiment", "test", "trial", "uncertain", "option"},
}


class ExecutiveDecisionEngine:
    """Builds and evaluates a decision from request semantics and observed evidence."""

    def evaluate(
        self,
        founder_request: str,
        context: dict[str, Any],
        *,
        response_mode: str,
        decomposition: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        request = " ".join(founder_request.split())
        decomposition = decomposition or {}
        tokens = self._tokens(request)
        decision_requested = self._decision_requested(request, tokens, response_mode, decomposition)
        objective = str(decomposition.get("primary_objective") or self._objective(request, tokens, decision_requested))
        constraints = self._constraints(tokens, decomposition)
        criteria = self._criteria(tokens, constraints)
        evidence = self._evidence(context)
        options = self._options(request, objective, decision_requested, tokens, evidence)
        evaluated_options = self._evaluate_options(options, criteria, tokens, evidence)
        uncertainty = self._uncertainty(context, request, evaluated_options)
        recommendation = self._recommend(
            objective,
            decision_requested,
            evaluated_options,
            evidence,
            uncertainty,
            tokens,
        )
        risk = self._risk(tokens, recommendation, uncertainty, decomposition)
        presentation_mode = self._presentation_mode(
            decision_requested,
            risk,
            response_mode,
        )
        return {
            "objective": objective,
            "request_decomposition": decomposition,
            "decision_requested": decision_requested,
            "constraints": constraints,
            "evaluation_criteria": criteria,
            "evidence": evidence,
            "options": evaluated_options,
            "uncertainty": uncertainty,
            "recommendation": recommendation,
            "risk": risk,
            "presentation_mode": presentation_mode,
            "estimated_effort": self._effort(tokens, recommendation, risk),
            "business_impact": self._business_impact(objective, recommendation, evidence),
            "consequence_of_inaction": self._consequence(objective, decision_requested, evidence),
            "next_action": self._next_action(decision_requested, recommendation, uncertainty, response_mode),
        }

    @staticmethod
    def _presentation_mode(
        decision_requested: str,
        risk: dict[str, Any],
        response_mode: str,
    ) -> str:
        if response_mode in {"casual", "clarify"}:
            return response_mode
        if risk.get("level") == "high":
            return "governed_action"
        modes = {
            "choose between competing investments": "comparison",
            "select the highest-value priority": "prioritization",
            "identify the highest-leverage improvement": "prioritization",
            "diagnose the limiting constraint": "diagnosis",
            "challenge the current direction": "critique",
            "remove low-value work": "critique",
            "sequence priorities over time": "roadmap",
            "decide whether the proposed change should proceed": "execution",
        }
        return modes.get(decision_requested, "prioritization")

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(WORD_RE.findall(text.lower().replace("-", " ")))

    @staticmethod
    def _objective(request: str, tokens: set[str], decision_requested: str) -> str:
        explicit = ExecutiveDecisionEngine._explicit_options(request)
        if len(explicit) >= 2:
            return "Choose how to allocate resources between " + " and ".join(option.lower() for option in explicit)
        if decision_requested == "diagnose the limiting constraint":
            subject = re.sub(r"^why\s+(?:do|does|are|is)\s+(?:we|i|the system)?\s*", "", request, flags=re.IGNORECASE).rstrip("?.")
            return "Identify why " + (subject or "the desired outcome is constrained")
        if decision_requested == "remove low-value work":
            return "Protect capacity by stopping work that does not complete a business outcome"
        if decision_requested == "challenge the current direction":
            return "Evaluate whether the current direction produces complete business outcomes"
        if decision_requested == "sequence priorities over time":
            return "Sequence the highest-value outcomes within the planning horizon"
        cleaned = re.sub(r"^(?:what|how)\s+", "", request.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"^(?:should|could|can|would)\s+(?:we|i)\s+", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^(?:we|i)\s+", "", cleaned, flags=re.IGNORECASE).rstrip("?.")
        cleaned = re.sub(r"\bnext$", "for the highest near-term value", cleaned, flags=re.IGNORECASE).strip()
        if cleaned.lower() in {"improve for the highest near-term value", "improve"}:
            return "Improve the highest-leverage area"
        concepts = [
            name
            for name, vocabulary in CONCEPT_WEIGHTS.items()
            if tokens & vocabulary
        ]
        if cleaned:
            return cleaned[0].upper() + cleaned[1:]
        if concepts:
            return "Improve " + " and ".join(concepts)
        return "Clarify the desired business outcome"

    @staticmethod
    def _decision_requested(
        request: str,
        tokens: set[str],
        response_mode: str,
        decomposition: dict[str, Any],
    ) -> str:
        lowered = request.lower().strip()
        if response_mode in {"casual", "clarify"}:
            return response_mode
        requested_action = str(decomposition.get("requested_action") or "")
        if requested_action == "RECOMMEND" and ("stop" in tokens or "cut" in tokens):
            return "remove low-value work"
        if requested_action == "ANALYZE" and {"critique", "challenge", "wrong"} & tokens:
            return "challenge the current direction"
        if requested_action == "RECOMMEND" and {"critique", "challenge", "wrong"} & tokens:
            return "challenge the current direction"
        decomposed = {
            "ANALYZE": "diagnose the limiting constraint",
            "DIAGNOSE": "diagnose the limiting constraint",
            "COMPARE": "choose between competing investments",
            "RECOMMEND": "select the highest-value priority",
            "PLAN": "sequence priorities over time",
            "IMPLEMENT": "decide whether the proposed change should proceed",
            "GOVERNED_ACTION": "decide whether the proposed change should proceed",
            "QUESTION": "identify the highest-leverage improvement",
        }
        if requested_action in decomposed:
            return decomposed[requested_action]
        if " or " in lowered or " versus " in lowered or " vs " in lowered:
            return "choose between competing investments"
        if lowered.startswith("why") or {"diagnose", "cause"} & tokens:
            return "diagnose the limiting constraint"
        if "stop" in tokens or "cut" in tokens:
            return "remove low-value work"
        if {"90", "roadmap", "sequence", "plan"} & tokens:
            return "sequence priorities over time"
        if {"critique", "challenge", "wrong"} & tokens:
            return "challenge the current direction"
        if {"should", "priority", "prioritize", "next"} & tokens:
            return "select the highest-value priority"
        if response_mode == "implementation_handoff" or ACTION_WORDS & tokens:
            return "decide whether the proposed change should proceed"
        return "identify the highest-leverage improvement"

    @staticmethod
    def _constraints(tokens: set[str], decomposition: dict[str, Any]) -> list[str]:
        constraints = [
            str(item)
            for item in (decomposition.get("explicit_constraints") or [])
        ]
        if tokens & CONCEPT_WEIGHTS["capacity"]:
            constraints.append("Engineering capacity is constrained.")
        if tokens & CONCEPT_WEIGHTS["governance"]:
            constraints.append("Existing founder approval and production safeguards must remain in place.")
        if {"90", "days", "quarter"} & tokens:
            constraints.append("The decision must produce value within the stated planning horizon.")
        if {"fundraising", "investor", "demo"} & tokens:
            constraints.append("The decision must improve external credibility, not only add visible scope.")
        return constraints or ["Use current capacity carefully and preserve existing governance."]

    @staticmethod
    def _criteria(tokens: set[str], constraints: list[str]) -> list[dict[str, Any]]:
        criteria: list[dict[str, Any]] = []
        for name, signals in CRITERION_SIGNALS.items():
            overlap = len(tokens & signals)
            if overlap:
                criteria.append({"name": name, "weight": min(5, 2 + overlap), "reason": f"Relevant signals: {', '.join(sorted(tokens & signals))}."})
        present = {item["name"] for item in criteria}
        for name, weight in (("business impact", 4), ("time to value", 3), ("execution risk", 3)):
            if name not in present:
                criteria.append({"name": name, "weight": weight, "reason": "Default executive decision criterion."})
        if any("capacity" in item.lower() for item in constraints):
            for criterion in criteria:
                if criterion["name"] == "time to value":
                    criterion["weight"] = 5
        if any("planning horizon" in item.lower() for item in constraints):
            for criterion in criteria:
                if criterion["name"] == "time to value":
                    criterion["weight"] = 5
        return sorted(criteria, key=lambda item: (-int(item["weight"]), str(item["name"])))

    @staticmethod
    def _evidence(context: dict[str, Any]) -> list[dict[str, str]]:
        observations = context.get("observations") or {}
        evidence: list[dict[str, str]] = []
        mappings = (
            ("platform maturity", "platform_stage", "Company Intelligence"),
            ("estimated completion", "estimated_completion_percent", "Company Intelligence"),
            ("active missions", "active_missions", "Mission Pipeline"),
            ("blocked missions", "blocked_missions", "Mission Pipeline"),
            ("repository areas", "repository_areas_available", "Repository Intelligence"),
            ("engineering operating mode", "engineering_mode", "Engineering Manager"),
        )
        for label, key, source in mappings:
            value = observations.get(key)
            if value is not None:
                evidence.append({"fact": f"{label}: {value}", "source": source})
        if observations.get("pipeline_observer_only"):
            evidence.append({"fact": "mission status is observed from existing systems", "source": "Mission Pipeline"})
        return evidence

    def _options(
        self,
        request: str,
        objective: str,
        decision_requested: str,
        tokens: set[str],
        evidence: list[dict[str, str]],
    ) -> list[str]:
        explicit = self._explicit_options(request) if decision_requested == "choose between competing investments" else []
        if len(explicit) >= 2:
            growth_option = next((option for option in explicit if self._tokens(option) & CONCEPT_WEIGHTS["growth"]), None)
            reliability_option = next((option for option in explicit if self._tokens(option) & CONCEPT_WEIGHTS["reliability"]), None)
            if growth_option and reliability_option and tokens & CONCEPT_WEIGHTS["capacity"]:
                growth_outcome = self._noun_phrase(growth_option)
                reliability_work = self._noun_phrase(reliability_option)
                return [
                    f"Deliver the smallest credible {growth_outcome} and address only {reliability_work} that blocks it",
                    *explicit,
                ]
            return explicit
        focus = self._focus(tokens)
        if decision_requested == "diagnose the limiting constraint":
            return [
                f"Improve integration and completion across existing {focus}",
                f"Continue expanding {focus}",
                "Pause expansion and measure where founder journeys break",
            ]
        if decision_requested == "remove low-value work":
            return [
                f"Stop net-new {focus} until current journeys are complete",
                f"Reduce parallel work and keep only one outcome-focused {focus} mission",
                "Continue the current portfolio unchanged",
            ]
        if decision_requested == "sequence priorities over time":
            return [
                f"Complete and integrate current {focus} before expansion",
                f"Split capacity evenly between completion and new {focus}",
                f"Prioritize a new visible {focus} milestone first",
            ]
        if decision_requested == "challenge the current direction":
            completion = next((item["fact"] for item in evidence if item["fact"].startswith("estimated completion")), "")
            evidence_suffix = f" ({completion})" if completion else ""
            return [
                f"Narrow the product promise to one complete founder outcome{evidence_suffix}",
                "Continue expanding the current capability portfolio",
                "Pause roadmap expansion and validate which outcome founders value most",
            ]
        if decision_requested in {"select the highest-value priority", "identify the highest-leverage improvement"}:
            completion = next((item["fact"] for item in evidence if item["fact"].startswith("estimated completion")), "")
            evidence_suffix = f" ({completion})" if completion else ""
            return [
                f"Complete one end-to-end founder mission journey{evidence_suffix}",
                "Improve reliability and integration across existing capabilities",
                f"Expand {focus} with a new visible feature",
            ]
        return [
            f"Make a focused improvement to {objective.lower()}",
            f"Broaden the initiative across adjacent {focus}",
            "Defer action until stronger evidence is available",
        ]

    @staticmethod
    def _explicit_options(request: str) -> list[str]:
        body = request.strip().rstrip("?.")
        parts = re.split(r"\s+(?:or|versus|vs\.?)(?:\s+)", body, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) != 2:
            return []
        left = re.sub(r"^.*?\b(?:should|whether)\s+(?:we|i)\s+", "", parts[0], flags=re.IGNORECASE).strip()
        right = parts[1].strip()
        return [part[0].upper() + part[1:] for part in (left, right) if part]

    @staticmethod
    def _focus(tokens: set[str]) -> str:
        ranked = [
            (len(tokens & vocabulary), name)
            for name, vocabulary in CONCEPT_WEIGHTS.items()
        ]
        score, name = max(ranked)
        labels = {
            "capacity": "engineering delivery",
            "growth": "growth",
            "reliability": "reliability",
            "experience": "founder experience",
            "governance": "governed operations",
            "coherence": "platform capabilities",
        }
        return labels[name] if score else "platform capabilities"

    @staticmethod
    def _noun_phrase(option: str) -> str:
        phrase = re.sub(
            r"^(?:build|fix|improve|create|deliver|prioritize)\s+",
            "",
            option.strip(),
            flags=re.IGNORECASE,
        ).lower()
        return re.sub(r"^(?:the|a|an)\s+", "", phrase)

    def _evaluate_options(
        self,
        options: list[str],
        criteria: list[dict[str, Any]],
        request_tokens: set[str],
        evidence: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        evidence_text = " ".join(item["fact"].lower() for item in evidence)
        evaluated: list[dict[str, Any]] = []
        for position, option in enumerate(options):
            option_tokens = self._tokens(option)
            criterion_scores: dict[str, int] = {}
            total = 0
            total_weight = 0
            for criterion in criteria:
                name = str(criterion["name"])
                weight = int(criterion["weight"])
                signals = CRITERION_SIGNALS.get(name, set())
                relevance = len(option_tokens & signals) + len(request_tokens & option_tokens)
                score = 3
                if "defer" in option_tokens or "unchanged" in option_tokens:
                    score = 2 if name in {"business impact", "time to value"} else 4
                elif {"complete", "integrate", "focused", "reduce"} & option_tokens:
                    score = 5 if name in {"strategic coherence", "time to value", "operational reliability"} else 4
                elif {"broaden", "expanding", "new"} & option_tokens:
                    score = 4 if name == "business impact" else 2
                if option_tokens & signals:
                    score += 1
                if name == "time to value" and {"smallest", "credible", "demo", "focused"} & option_tokens:
                    score += 1
                if name == "business impact" and option_tokens & CONCEPT_WEIGHTS["growth"]:
                    score += 1
                if name == "operational reliability" and option_tokens & CONCEPT_WEIGHTS["reliability"]:
                    score += 1
                score = min(5, score + min(1, relevance))
                criterion_scores[name] = score
                total += score * weight
                total_weight += 5 * weight
            evidence_bonus = 2 if "completion" in evidence_text and {"complete", "integrate"} & option_tokens else 0
            confidence_score = round(100 * (total + evidence_bonus) / max(total_weight + evidence_bonus, 1))
            evaluated.append(
                {
                    "option": option,
                    "score": confidence_score,
                    "criteria": criterion_scores,
                    "trade_off": self._trade_off(option_tokens, position),
                }
            )
        return sorted(evaluated, key=lambda item: -int(item["score"]))

    @staticmethod
    def _trade_off(tokens: set[str], position: int) -> str:
        if "defer" in tokens or "unchanged" in tokens:
            return "Preserves capacity now but delays learning and business value."
        if {"stop", "reduce", "complete", "integrate", "focused"} & tokens:
            return "Concentrates capacity and improves coherence, with fewer new capabilities in the near term."
        if {"broaden", "expanding", "new"} & tokens:
            return "Creates visible scope but increases fragmentation and completion risk."
        return "Balances near-term progress against uncertainty in the available evidence." if position else "Directly addresses the stated objective with controlled scope."

    @staticmethod
    def _uncertainty(
        context: dict[str, Any],
        request: str,
        options: list[dict[str, Any]],
    ) -> list[str]:
        uncertainty: list[str] = []
        unavailable = [
            name.replace("_", " ")
            for name, status in (context.get("source_status") or {}).items()
            if status == "unavailable"
        ]
        if unavailable:
            uncertainty.append("Unavailable context: " + ", ".join(unavailable) + ".")
        lowered = request.lower()
        if any(term in lowered for term in ("fundraising", "investor", "revenue", "customer")):
            uncertainty.append("Current investor, revenue, and customer evidence is not available in the retrieved context.")
        if len(options) < 2:
            uncertainty.append("The request does not yet contain enough viable alternatives for a trade-off decision.")
        return uncertainty or ["No material context gap was detected, but estimates remain directional."]

    @staticmethod
    def _recommend(
        objective: str,
        decision_requested: str,
        options: list[dict[str, Any]],
        evidence: list[dict[str, str]],
        uncertainty: list[str],
        tokens: set[str],
    ) -> dict[str, str]:
        selected = options[0]
        option = str(selected["option"])
        evidence_fact = evidence[1]["fact"] if len(evidence) > 1 else (evidence[0]["fact"] if evidence else "live operating evidence is limited")
        if decision_requested == "diagnose the limiting constraint":
            action = option
            rationale = f"The evidence points to a completion and coherence constraint rather than a lack of capability; {evidence_fact}."
        elif decision_requested == "remove low-value work":
            action = option
            rationale = "Capacity should be protected from work that expands surface area without completing a founder or customer outcome."
        elif "fundraising" in tokens or "investor" in tokens:
            action = option
            rationale = "The strongest choice is the one that improves demonstrable credibility fastest; external outcome data is still uncertain."
        elif decision_requested == "sequence priorities over time":
            action = option
            rationale = "Sequencing completion before expansion compounds reliability and reduces parallel-work drag."
        else:
            action = option
            rationale = f"It best matches the weighted criteria for {objective.lower()} while keeping the decision reversible."
        confidence = "medium" if any("not available" in item for item in uncertainty) else "high"
        return {"action": action, "why": rationale, "confidence": confidence}

    @staticmethod
    def _risk(
        tokens: set[str],
        recommendation: dict[str, str],
        uncertainty: list[str],
        decomposition: dict[str, Any],
    ) -> dict[str, Any]:
        execution_requested = bool(decomposition.get("execution_requested"))
        governed = bool(decomposition.get("governed_action_requested")) or (
            execution_requested and bool(tokens & CONCEPT_WEIGHTS["governance"])
        )
        material_uncertainty = any("not available" in item or "Unavailable" in item for item in uncertainty)
        level = "high" if governed else ("moderate" if material_uncertainty else "low")
        return {
            "level": level,
            "factors": [
                "The decision touches a governed production or repository capability."
                if governed
                else (
                    "Important business evidence is missing."
                    if material_uncertainty
                    else "The recommendation is focused and reversible."
                )
            ],
            "mitigations": ["Validate the leading assumption before irreversible action.", "Preserve existing founder approval gates."],
            "impact_if_fail": "Capacity is consumed without producing the intended business outcome.",
        }

    @staticmethod
    def _effort(
        tokens: set[str],
        recommendation: dict[str, str],
        risk: dict[str, Any],
    ) -> str:
        if {"small", "polish", "copy", "styling"} & tokens and risk["level"] == "low":
            return "Approximately 30-60 minutes for planning and implementation."
        if "90" in tokens or "roadmap" in tokens:
            return "A 90-day sequence with review points every two to four weeks."
        if risk["level"] == "high":
            return "A detailed safeguard review is required before estimating execution."
        return "Approximately 1-3 hours to validate and prepare the first decision-ready step."

    @staticmethod
    def _business_impact(
        objective: str,
        recommendation: dict[str, str],
        evidence: list[dict[str, str]],
    ) -> str:
        evidence_note = evidence[2]["fact"] if len(evidence) > 2 else "current operating context is available"
        return f"Advances {objective.lower()} by concentrating effort on the highest-scoring option; {evidence_note}."

    @staticmethod
    def _consequence(
        objective: str,
        decision_requested: str,
        evidence: list[dict[str, str]],
    ) -> str:
        if decision_requested == "diagnose the limiting constraint":
            return "The system may continue accumulating capabilities while the founder experience remains fragmented."
        if decision_requested == "remove low-value work":
            return "Capacity remains spread across work that may not complete a meaningful business outcome."
        if decision_requested == "choose between competing investments":
            return "The choice will be made implicitly through fragmented capacity allocation rather than an explicit business priority."
        return f"Current operations continue, but progress toward {objective.lower()} is delayed."

    @staticmethod
    def _next_action(
        decision_requested: str,
        recommendation: dict[str, str],
        uncertainty: list[str],
        response_mode: str,
    ) -> str:
        if response_mode == "casual":
            return "Continue the conversation."
        if response_mode == "clarify":
            return "Clarify the desired business outcome."
        if recommendation["confidence"] == "medium":
            return "Validate the missing evidence, then make the decision using the ranked options."
        if decision_requested == "diagnose the limiting constraint":
            return "Confirm the limiting constraint and prioritize one end-to-end outcome."
        return "Approve the recommended priority and convert it into one focused mission."
