"""
Tests for the real, LLM-backed CEO/CTO/manager-tier agent handlers.

Tests are Python 3.9 compatible - no match/case, no PEP 604 unions.
Uses unittest.mock.patch to stub invoke_provider so these run deterministically
without real AI provider credentials.
"""
from __future__ import annotations

import os
import tempfile

# Must happen before app.platform.persistence.database is first imported anywhere in
# this process (directly or transitively) - that module resolves its DB engine once at
# import time from PLATFORM_DATABASE_URL/DATABASE_URL/.env, and a local dev .env can
# point at a real Postgres database that's missing tables this test creates fresh. Only
# sets it if not already explicitly configured, so a developer who wants to point this
# at a real database on purpose still can.
os.environ.setdefault(
    "PLATFORM_DATABASE_URL",
    "sqlite:///" + os.path.join(tempfile.mkdtemp(prefix="management_agents_test_"), "test_platform.db"),
)

import unittest
from unittest.mock import patch

from app.platform.agents.specialists import (
    _MANAGEMENT_AGENT_CONFIGS,
    _extract_management_decision,
    build_management_agent_handler,
    register_specialist_agents,
)
from app.platform.agents.builtin import register_builtin_agents
from app.platform.agents.registry import get_agent
from app.platform.runtime.ai_provider import AIProviderError, AIProviderResult
from app.platform.services.agent_workflow_executor_service import execute_agent_workflow
from app.platform.services.app_build_workflow_generator_service import generate_app_build_workflow


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


class PipelineBlockingTests(unittest.TestCase):
    """A manager's redirect/escalate must actually block downstream execution, not just
    be logged and ignored - this is the whole point of Phase 3/4. Runs the real
    generate_app_build_workflow() + execute_agent_workflow() pipeline (the same one
    /api/projects/{id}/build uses) with a controlled mock: every manager approves
    except backend_manager, which redirects. Confirms only the steps that actually
    depend on backend_manager (directly or transitively, e.g. builder, which fans in
    all three functional managers) get blocked - not a global failure, and not silently
    ignored either.
    """

    def setUp(self):
        from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables

        create_platform_tables()
        register_builtin_agents()
        register_specialist_agents()
        self.db = PlatformSessionLocal()

    def tearDown(self):
        self.db.close()

    def test_one_managers_redirect_blocks_the_fan_in_builder_step_and_everything_after(self):
        def fake_invoke(provider, prompt, system, model):
            if "Backend Manager" in system:
                return AIProviderResult(
                    status="completed",
                    provider="deepseek",
                    model="deepseek-v4-pro",
                    output_text=(
                        '{"decision": "redirect", "rationale": "Missing API auth.", '
                        '"concerns": ["No auth boundary defined."]}'
                    ),
                    raw={},
                )
            return AIProviderResult(
                status="completed",
                provider="deepseek",
                model="deepseek-v4-pro",
                output_text='{"decision": "approve", "rationale": "Looks fine.", "concerns": []}',
                raw={},
            )

        workflow = generate_app_build_workflow(app_request="Build a simple todo app")

        with patch("app.platform.agents.specialists.invoke_provider", side_effect=fake_invoke):
            result = execute_agent_workflow(
                self.db,
                steps=workflow["steps"],
                workflow_name=workflow["workflow_name"],
                simulation=False,
                log_event=False,
                persist_result=False,
            )

        statuses = {step["step_id"]: step["status"] for step in result["step_runs"]}

        # Everything up to and including the three functional managers ran for real.
        for step_id in ("ceo", "architecture", "cto", "engineering_manager", "frontend_manager", "database_manager"):
            self.assertEqual(statuses[step_id], "completed", "%s should have completed" % step_id)

        # backend_manager itself is the one that redirected.
        self.assertEqual(statuses["backend_manager"], "failed")

        # Everything that requires backend_manager (directly or transitively) must be
        # blocked - not completed, not silently skipped as if nothing happened.
        for step_id in ("builder", "review", "quality_manager", "test"):
            self.assertEqual(
                statuses[step_id],
                "blocked",
                "%s must be blocked once backend_manager redirects - a manager's "
                "disapproval must not be silently ignored" % step_id,
            )

        self.assertEqual(result["status"], "blocked")
        self.assertGreater(result["blocked_step_count"], 0)
        self.assertEqual(result["failed_step_count"], 1)


if __name__ == "__main__":
    unittest.main()
