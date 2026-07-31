"""
Tests for the real, LLM-backed CEO/CTO/manager-tier agent handlers.

Tests are Python 3.9 compatible - no match/case, no PEP 604 unions.
Uses unittest.mock.patch to stub invoke_provider so these run deterministically
without real AI provider credentials.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from app.platform.agents.specialists import (
    _MANAGEMENT_AGENT_CONFIGS,
    _extract_management_decision,
    build_management_agent_handler,
    register_specialist_agents,
)
from app.platform.agents.registry import get_agent
from app.platform.runtime.ai_provider import AIProviderError, AIProviderResult


def _fake_result(output_text, status="completed", provider="deepseek", model="deepseek-v4-pro"):
    return AIProviderResult(status=status, provider=provider, model=model, output_text=output_text, raw={})


class ExtractManagementDecisionTests(unittest.TestCase):
    def test_plain_json(self):
        self.assertEqual(
            _extract_management_decision('{"decision": "approve", "rationale": "x"}'),
            {"decision": "approve", "rationale": "x"},
        )

    def test_json_in_code_fence(self):
        self.assertEqual(
            _extract_management_decision('```json\n{"decision": "redirect"}\n```'),
            {"decision": "redirect"},
        )

    def test_non_json_returns_empty_dict(self):
        self.assertEqual(_extract_management_decision("not json at all"), {})
        self.assertEqual(_extract_management_decision(""), {})


class ManagementAgentRegistrationTests(unittest.TestCase):
    def setUp(self):
        register_specialist_agents()

    def test_all_seven_roles_are_registered_with_distinct_handlers(self):
        agent_ids = [config[0] for config in _MANAGEMENT_AGENT_CONFIGS]
        self.assertEqual(
            sorted(agent_ids),
            sorted(
                [
                    "ceo_agent",
                    "cto_agent",
                    "engineering_manager_agent",
                    "backend_manager_agent",
                    "frontend_manager_agent",
                    "database_manager_agent",
                    "quality_manager_agent",
                ]
            ),
        )
        handlers = set()
        for agent_id in agent_ids:
            agent = get_agent(agent_id)
            self.assertIsNotNone(agent, "%s must be registered" % agent_id)
            handlers.add(agent.handler)
        self.assertEqual(len(handlers), 7, "each of the 7 roles must have its own distinct handler closure")


class ManagementAgentDecisionShapeTests(unittest.TestCase):
    def _handler(self, reviews_step_id=None):
        return build_management_agent_handler(
            agent_id="cto_agent",
            name="CTO Agent",
            role_description="Evaluates the technical architecture plan for soundness.",
            reviews_step_id=reviews_step_id,
        )

    def test_no_longer_returns_old_stub_shape(self):
        handler = self._handler()
        with patch(
            "app.platform.agents.specialists.invoke_provider",
            return_value=_fake_result('{"decision": "approve", "rationale": "Looks solid."}'),
        ):
            result = handler({"input_payload": {"goal": "Build a todo app"}})

        # Old stub shape: {"agent_id": "management_agent", "delegation_report": {...}}
        self.assertNotEqual(result.get("agent_id"), "management_agent")
        self.assertNotIn("delegation_report", result)
        self.assertIn("decision", result)
        self.assertIn("rationale", result)
        self.assertIn("concerns", result)

    def test_approve_sets_success_true(self):
        handler = self._handler()
        with patch(
            "app.platform.agents.specialists.invoke_provider",
            return_value=_fake_result('{"decision": "approve", "rationale": "Fine.", "concerns": []}'),
        ):
            result = handler({"input_payload": {"goal": "Build a todo app"}})
        self.assertEqual(result["decision"], "approve")
        self.assertTrue(result["success"])

    def test_redirect_sets_success_false(self):
        handler = self._handler()
        with patch(
            "app.platform.agents.specialists.invoke_provider",
            return_value=_fake_result(
                '{"decision": "redirect", "rationale": "Missing pagination.", '
                '"concerns": ["No pagination on the list endpoint."]}'
            ),
        ):
            result = handler({"input_payload": {"goal": "Build a todo app"}})
        self.assertEqual(result["decision"], "redirect")
        self.assertFalse(
            result["success"],
            "a redirect must set success=False so dependency_failed_or_blocked() actually "
            "blocks downstream steps, not just log the disagreement",
        )
        self.assertIn("No pagination", result["concerns"][0])

    def test_escalate_sets_success_false(self):
        handler = self._handler()
        with patch(
            "app.platform.agents.specialists.invoke_provider",
            return_value=_fake_result('{"decision": "escalate", "rationale": "Needs a founder call."}'),
        ):
            result = handler({"input_payload": {"goal": "Build a todo app"}})
        self.assertEqual(result["decision"], "escalate")
        self.assertFalse(result["success"])


class ManagementAgentSafetyEscalationTests(unittest.TestCase):
    """A handler must never silently 'approve' when it can't actually form an opinion."""

    def setUp(self):
        self.handler = build_management_agent_handler(
            agent_id="quality_manager_agent",
            name="Quality Manager Agent",
            role_description="Final quality gate.",
            reviews_step_id="review",
        )
        self.task = {"input_payload": {"goal": "Build a todo app"}}

    def test_provider_error_escalates(self):
        with patch(
            "app.platform.agents.specialists.invoke_provider",
            side_effect=AIProviderError("DEEPSEEK_API_KEY is not configured"),
        ):
            result = self.handler(self.task)
        self.assertEqual(result["decision"], "escalate")
        self.assertFalse(result["success"])

    def test_non_completed_status_escalates(self):
        with patch(
            "app.platform.agents.specialists.invoke_provider",
            return_value=_fake_result("", status="missing-secret"),
        ):
            result = self.handler(self.task)
        self.assertEqual(result["decision"], "escalate")
        self.assertFalse(result["success"])

    def test_unparsable_output_escalates(self):
        with patch(
            "app.platform.agents.specialists.invoke_provider",
            return_value=_fake_result("I think this looks fine, approved!"),
        ):
            result = self.handler(self.task)
        self.assertEqual(result["decision"], "escalate")
        self.assertFalse(result["success"])

    def test_invalid_decision_value_escalates(self):
        with patch(
            "app.platform.agents.specialists.invoke_provider",
            return_value=_fake_result('{"decision": "maybe", "rationale": "unsure"}'),
        ):
            result = self.handler(self.task)
        self.assertEqual(result["decision"], "escalate")
        self.assertFalse(result["success"])


class ManagementAgentArtifactThreadingTests(unittest.TestCase):
    def test_ceo_has_no_reviewed_step_and_evaluates_the_goal_directly(self):
        handler = build_management_agent_handler(
            agent_id="ceo_agent", name="CEO Agent", role_description="CEO.", reviews_step_id=None
        )
        captured = {}

        def fake_invoke(**kwargs):
            captured.update(kwargs)
            return _fake_result('{"decision": "approve", "rationale": "Reasonable request."}')

        with patch("app.platform.agents.specialists.invoke_provider", side_effect=fake_invoke):
            result = handler({"input_payload": {"goal": "Build a vacation tracker"}})

        self.assertIsNone(result["reviewed_step"])
        self.assertIn("Build a vacation tracker", captured["prompt"])
        self.assertIn("evaluating the founder's request itself", captured["prompt"])

    def test_cto_receives_the_actual_architecture_artifact_not_a_free_text_question(self):
        handler = build_management_agent_handler(
            agent_id="cto_agent",
            name="CTO Agent",
            role_description="Evaluates architecture.",
            reviews_step_id="architecture",
        )
        captured = {}

        def fake_invoke(**kwargs):
            captured.update(kwargs)
            return _fake_result('{"decision": "approve", "rationale": "Sound plan."}')

        task = {
            "input_payload": {
                "goal": "Build a todo app",
                "workflow_context": {
                    "dependency_outputs": {
                        "architecture": {
                            "step_id": "architecture",
                            "selected_agent": {"agent_id": "architect_agent"},
                            "output": {
                                "handler_result": {
                                    "architecture_plan": {
                                        "architecture_summary": "FastAPI backend, single Task model.",
                                    }
                                }
                            },
                        }
                    }
                },
            }
        }
        with patch("app.platform.agents.specialists.invoke_provider", side_effect=fake_invoke):
            handler(task)

        self.assertIn("FastAPI backend, single Task model", captured["prompt"])
        self.assertIn("Build a todo app", captured["prompt"])
        self.assertIsNone(captured["provider"], "should default to the platform-selected provider, not force one")


if __name__ == "__main__":
    unittest.main()
