from __future__ import annotations

from app.platform.learning.confidence_engine import confidence_label, confidence_score
from app.platform.learning.experience_store import ExperienceRecord, add_experience, successful_experiences
from app.platform.learning.feedback_processor import apply_quality_feedback, outcome_from_feedback
from app.platform.learning.learning_engine import decision_intelligence
from app.platform.learning.optimization_engine import optimization_hint
from app.platform.learning.pattern_detector import agent_success_rates, success_rate
from app.platform.learning.recommendation_engine import recommend_agent


def main() -> None:
    records = []
    records = add_experience(
        records,
        ExperienceRecord(
            experience_id="exp1",
            task_type="backend_api",
            agent_id="backend_builder_agent",
            outcome="success",
            duration_seconds=600,
            retry_count=0,
            recovery_action=None,
            quality_score=90,
        ),
    )
    records = add_experience(
        records,
        ExperienceRecord(
            experience_id="exp2",
            task_type="backend_api",
            agent_id="backend_builder_agent",
            outcome="success",
            duration_seconds=720,
            retry_count=1,
            recovery_action="retry",
            quality_score=85,
        ),
    )

    assert len(successful_experiences(records)) == 2
    assert success_rate(records, "backend_api") == 1.0
    assert agent_success_rates(records)["backend_builder_agent"] == 1.0

    score = confidence_score(records, "backend_api")
    assert score == 2, score
    assert confidence_label(score) == "low"

    recommendation = recommend_agent(records, "backend_api")
    assert recommendation["agent_id"] == "backend_builder_agent", recommendation
    assert optimization_hint(recommendation) == "collect_more_data"

    updated = apply_quality_feedback(records[0], 60)
    assert updated.quality_score == 60, updated
    assert outcome_from_feedback(60) == "failed"

    decision = decision_intelligence(records, "backend_api")
    assert decision["recommendation"]["agent_id"] == "backend_builder_agent", decision

    print("LEARNING CHECK PASSED")


if __name__ == "__main__":
    main()
