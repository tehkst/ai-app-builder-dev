from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Sequence, Tuple

from app.platform.events.company_brain_learning_models import (
    LearnedLesson,
    LearningCandidate,
    LearningPattern,
    LearningSummary,
)
from app.platform.events.company_brain_reasoning_models import ActionExecution, ExecutionRun


class CompanyBrainLearningEngine:
    """Derive deterministic, evidence-bound learning from execution outcomes."""

    def learn_from_execution(self, run: ExecutionRun) -> LearningSummary:
        return self.learn_from_executions((run,))

    def learn_from_executions(self, runs: Sequence[ExecutionRun]) -> LearningSummary:
        normalized = _validated_runs(runs)
        mission = normalized[0].mission
        if any(run.mission.key != mission.key for run in normalized):
            raise ValueError("all execution runs must belong to the same mission")

        candidates = tuple(
            candidate
            for run in normalized
            for candidate in _candidates(run)
        )
        lessons = tuple(_lesson(candidate) for candidate in candidates if candidate.authoritative)
        patterns = _patterns(normalized)
        supporting_event_ids = _supporting_event_ids(normalized, candidates, lessons, patterns)
        warnings = _warnings(normalized, candidates, lessons)
        authoritative = bool(lessons) and all(lesson.authoritative for lesson in lessons)

        return LearningSummary(
            mission=mission,
            candidates=candidates,
            lessons=lessons,
            patterns=patterns,
            warnings=warnings,
            supporting_event_ids=supporting_event_ids,
            authoritative=authoritative,
        )


def _validated_runs(runs: Sequence[ExecutionRun]) -> Tuple[ExecutionRun, ...]:
    values = tuple(runs)
    if not values:
        raise ValueError("at least one execution run is required")
    if any(not isinstance(run, ExecutionRun) for run in values):
        raise TypeError("runs must contain only ExecutionRun values")
    return values


def _candidates(run: ExecutionRun) -> Tuple[LearningCandidate, ...]:
    return tuple(
        _candidate(run, execution)
        for execution in sorted(run.action_executions, key=lambda item: item.sequence)
    )


def _candidate(run: ExecutionRun, execution: ActionExecution) -> LearningCandidate:
    evidence = tuple(dict.fromkeys(execution.supporting_event_ids or run.supporting_event_ids))
    authoritative = (
        run.authoritative
        and run.status == "completed"
        and execution.status == "completed"
        and bool(evidence)
    )
    confidence = _confidence(run, execution, evidence)
    outcome = execution.status
    return LearningCandidate(
        code="ACTION_%s_%s" % (execution.action_code, outcome.upper()),
        title="Learn from %s" % execution.action_code,
        description=(
            "Action %s finished with status %s. %s"
            % (execution.action_code, outcome, execution.message or "No execution message was supplied.")
        ),
        outcome=outcome,
        confidence=confidence,
        target_entities=execution.target_entities,
        supporting_event_ids=evidence,
        authoritative=authoritative,
    )


def _confidence(
    run: ExecutionRun,
    execution: ActionExecution,
    evidence: Tuple[str, ...],
) -> float:
    if not evidence:
        return 0.0
    if run.authoritative and run.status == "completed" and execution.status == "completed":
        return 1.0
    if execution.status == "failed":
        return 0.6
    if execution.status == "blocked":
        return 0.3
    if execution.status == "pending":
        return 0.2
    if execution.status == "skipped":
        return 0.1
    return 0.4


def _lesson(candidate: LearningCandidate) -> LearnedLesson:
    return LearnedLesson(
        code="LESSON_%s" % candidate.code,
        statement=(
            "%s is a governed successful execution outcome supported by recorded evidence."
            % candidate.title.replace("Learn from ", "")
        ),
        outcome=candidate.outcome,
        confidence=candidate.confidence,
        target_entities=candidate.target_entities,
        supporting_event_ids=candidate.supporting_event_ids,
        authoritative=True,
    )


def _patterns(runs: Tuple[ExecutionRun, ...]) -> Tuple[LearningPattern, ...]:
    grouped = defaultdict(list)
    for run in runs:
        for execution in run.action_executions:
            grouped[(execution.action_code, execution.status)].append((run, execution))

    patterns = []
    for (action_code, outcome), occurrences in sorted(grouped.items()):
        if len(occurrences) < 2:
            continue
        event_ids = tuple(
            dict.fromkeys(
                event_id
                for run, execution in occurrences
                for event_id in (execution.supporting_event_ids or run.supporting_event_ids)
                if event_id
            )
        )
        authoritative = bool(event_ids) and all(
            run.authoritative
            and run.status == "completed"
            and execution.status == "completed"
            for run, execution in occurrences
        )
        patterns.append(
            LearningPattern(
                code="PATTERN_%s_%s" % (action_code, outcome.upper()),
                action_code=action_code,
                outcome=outcome,
                occurrences=len(occurrences),
                confidence=1.0 if authoritative else 0.5 if event_ids else 0.0,
                supporting_event_ids=event_ids,
                authoritative=authoritative,
            )
        )
    return tuple(patterns)


def _warnings(
    runs: Tuple[ExecutionRun, ...],
    candidates: Tuple[LearningCandidate, ...],
    lessons: Tuple[LearnedLesson, ...],
) -> Tuple[str, ...]:
    values = []
    if any(not run.authoritative for run in runs):
        values.append("One or more execution runs are non-authoritative.")
    if any(not candidate.supporting_event_ids for candidate in candidates):
        values.append("One or more learning candidates have no supporting event evidence.")
    if candidates and not lessons:
        values.append("No candidate qualified as governed authoritative learning.")
    return tuple(values)


def _supporting_event_ids(
    runs: Tuple[ExecutionRun, ...],
    candidates: Tuple[LearningCandidate, ...],
    lessons: Tuple[LearnedLesson, ...],
    patterns: Tuple[LearningPattern, ...],
) -> Tuple[str, ...]:
    values: Iterable[str] = (
        event_id
        for collection in (
            tuple(event_id for run in runs for event_id in run.supporting_event_ids),
            tuple(event_id for item in candidates for event_id in item.supporting_event_ids),
            tuple(event_id for item in lessons for event_id in item.supporting_event_ids),
            tuple(event_id for item in patterns for event_id in item.supporting_event_ids),
        )
        for event_id in collection
    )
    return tuple(dict.fromkeys(value for value in values if value))
