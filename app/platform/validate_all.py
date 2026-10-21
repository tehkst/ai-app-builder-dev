import argparse
import json
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict, List

COMMANDS = [
    {"name": "compatibility_scanner", "command": [sys.executable, "-m", "app.platform.compatibility.scanner"]},
    {"name": "compatibility_scanner_contract", "command": [sys.executable, "-m", "app.platform.compatibility.scanner_check"]},
    {"name": "validation_architecture", "command": [sys.executable, "-m", "app.platform.validation.architecture_check"]},
    {"name": "dependency_policy", "command": [sys.executable, "-m", "app.platform.compatibility.validate_dependency_policy"]},
    {"name": "platform_routes", "command": [sys.executable, "-m", "app.platform.api.validate_routes"]},
    {"name": "frontend_contract", "command": [sys.executable, "-m", "app.platform.frontend.validate_frontend_contract"]},
    {"name": "frontend_build", "command": [sys.executable, "-m", "app.platform.frontend.validate_frontend_build"]},
    {"name": "security_report", "command": [sys.executable, "-m", "app.platform.security_report"]},
    {"name": "generation_graph", "command": [sys.executable, "test_graph.py"]},
    {"name": "artifact_registry", "command": [sys.executable, "-m", "app.platform.artifacts.registry_report"]},
    {"name": "v100_workflow", "command": [sys.executable, "-m", "app.platform.agents.v100_workflow_check"]},
    {"name": "management_hierarchy", "command": [sys.executable, "-m", "app.platform.agents.management_hierarchy_check"]},
    {"name": "agent_manifest", "command": [sys.executable, "-m", "app.platform.agents.manifest_check"]},
    {"name": "agent_manifest_sync", "command": [sys.executable, "-m", "app.platform.agents.manifest_registry_sync_check"]},
    {"name": "organization_hierarchy", "command": [sys.executable, "-m", "app.platform.organization.organization_check"]},
    {"name": "engineering_memory", "command": [sys.executable, "-m", "app.platform.memory.memory_check"]},
    {"name": "engineering_knowledge_graph", "command": [sys.executable, "-m", "app.platform.knowledge.knowledge_check"]},
    {"name": "engineering_management", "command": [sys.executable, "-m", "app.platform.management.management_check"]},
    {"name": "pmo", "command": [sys.executable, "-m", "app.platform.pmo.pmo_check"]},
    {"name": "pmo_planning", "command": [sys.executable, "-m", "app.platform.pmo.planning_check"]},
    {"name": "pmo_graph", "command": [sys.executable, "-m", "app.platform.pmo.graph_check"]},
    {"name": "constitution", "command": [sys.executable, "-m", "app.platform.constitution.constitution_check"]},
    {"name": "delegation", "command": [sys.executable, "-m", "app.platform.delegation.delegation_check"]},
    {"name": "delegation_scheduler", "command": [sys.executable, "-m", "app.platform.delegation.scheduler_check"]},
    {"name": "delegation_manager", "command": [sys.executable, "-m", "app.platform.delegation.manager_check"]},
    {"name": "runtime", "command": [sys.executable, "-m", "app.platform.runtime.check_runtime"]},
    {"name": "runtime_engine", "command": [sys.executable, "-m", "app.platform.runtime.runtime_engine_check"]},
    {"name": "runtime_recovery", "command": [sys.executable, "-m", "app.platform.runtime.runtime_recovery_check"]},
    {"name": "event_bus", "command": [sys.executable, "-m", "app.platform.events.event_check"]},
    {"name": "self_healing", "command": [sys.executable, "-m", "app.platform.self_healing.self_healing_check"]},
    {"name": "plugin_architecture", "command": [sys.executable, "-m", "app.platform.plugins.plugin_check"]},
    {"name": "nautilus_loop", "command": [sys.executable, "-m", "app.platform.nautilus.loop_check"]},
    {"name": "nautilus_recipes", "command": [sys.executable, "-m", "app.platform.nautilus.recipe_check"]},
    {"name": "nautilus_http", "command": [sys.executable, "-m", "app.platform.nautilus.http_check"]},
    {"name": "nautilus_repair_flow", "command": [sys.executable, "-m", "app.platform.agents.nautilus_repair_flow_check"]},
    {"name": "orca_orchestrator", "command": [sys.executable, "-m", "app.platform.orca.orca_check"]},
    {"name": "orca_api", "command": [sys.executable, "-m", "app.platform.orca.api_check"]},
    {"name": "import_integrity", "command": [sys.executable, "-m", "app.platform.import_integrity_check"]},
    {"name": "codebase_health", "command": [sys.executable, "-m", "app.platform.codebase_health.check"]},
    {"name": "container_sandbox", "command": [sys.executable, "-m", "app.platform.container_sandbox.check"]},
    {"name": "clients", "command": [sys.executable, "-m", "app.platform.clients.check"]},
    {"name": "client_work", "command": [sys.executable, "-m", "app.platform.clients.work_check"]},
    {"name": "client_delivery", "command": [sys.executable, "-m", "app.platform.clients.delivery_check"]},
    {"name": "architecture_map", "command": [sys.executable, "-m", "app.platform.architecture_map_check"]},
    {"name": "mission_control_v2", "command": [sys.executable, "-m", "app.platform.ui.mc2.mc2_check"]},
    {"name": "orca_live_mission", "command": [sys.executable, "-m", "app.platform.orca.live_mission_check"]},
    {"name": "nautilus_live_smoke", "command": [sys.executable, "-m", "app.platform.nautilus.live_smoke_check"]},
    {"name": "decision_intelligence", "command": [sys.executable, "-m", "app.platform.learning.learning_check"]},
    {"name": "platform_registry", "command": [sys.executable, "-m", "app.platform.registry.registry_check"]},
    {"name": "deployment_platform", "command": [sys.executable, "-m", "app.platform.deployment.deployment_check"]},
    {"name": "operations_center", "command": [sys.executable, "-m", "app.platform.operations.operations_check"]},
    {"name": "admin_console", "command": [sys.executable, "-m", "app.platform.webconsole.console_check"]},
    {"name": "api_gateway", "command": [sys.executable, "-m", "app.platform.api_gateway.gateway_check"]},
    {"name": "auth_foundation", "command": [sys.executable, "-m", "app.platform.auth.auth_check"]},
    {"name": "login_boundary", "command": [sys.executable, "-m", "app.platform.auth.login_boundary_check"]},
    {"name": "saas_portal", "command": [sys.executable, "-m", "app.platform.saas_portal.portal_check"]},
    {"name": "platform_integration", "command": [sys.executable, "-m", "app.platform.integration.integration_check"]},
    {"name": "application_lifecycle", "command": [sys.executable, "-m", "app.platform.lifecycle.lifecycle_check"]},
    {"name": "subscription_management", "command": [sys.executable, "-m", "app.platform.billing.billing_check"]},
    {"name": "executive_intelligence", "command": [sys.executable, "-m", "app.platform.executive_intelligence.executive_intelligence_check"]},
    {"name": "founder_conversation_orchestration", "command": [sys.executable, "-m", "app.platform.board_room.afos_011_founder_conversation_check"]},
    {"name": "founder_decision_experience", "command": [sys.executable, "-m", "app.platform.founder_decision.afos_012_check"]},
    {"name": "conversational_workflow", "command": [sys.executable, "-m", "app.platform.founder_decision.afos_012_1_check"]},
    {"name": "architecture_intent_fidelity", "command": [sys.executable, "-m", "app.platform.board_room.architecture_intent_fidelity_check"]},
    {"name": "intent_taxonomy", "command": [sys.executable, "-m", "app.platform.board_room.intent_taxonomy_check"]},
    {"name": "jarvis_live_bug_regression", "command": [sys.executable, "-m", "app.platform.board_room.jarvis_live_bug_regression_check"]},
    {"name": "software_delivery", "command": [sys.executable, "-m", "app.platform.operating_console.afos_013_delivery_check"]},
    {"name": "provider_independent_delivery", "command": [sys.executable, "-m", "app.platform.operating_console.provider_independence_check"]},
    {"name": "artifact_qualification_target", "command": [sys.executable, "-m", "app.platform.artifacts.qualification_target_check"]},
    {"name": "architecture_knowledge_graph", "command": [sys.executable, "-m", "app.platform.architecture_knowledge_graph.check"]},
    {"name": "control_flow_projection", "command": [sys.executable, "-m", "app.platform.architecture_knowledge_graph.control_flow_check"]},
    {"name": "ui_ux_agent_preview_registry", "command": [sys.executable, "-m", "app.platform.ui_ux_agent.check"]},
    {"name": "autonomous_delivery_lineage", "command": [sys.executable, "-m", "app.platform.delivery_lineage.check"]},
    {"name": "full_saas_factory", "command": [sys.executable, "-m", "app.platform.saas_builder.check"]},
    {"name": "cloud_run_github_workspace", "command": [sys.executable, "-m", "app.platform.github_execution.cloud_run_workspace_check"]},
    {"name": "founder_workflow", "command": [sys.executable, "-m", "app.platform.founder_workflow.workflow_check"]},
    {"name": "conversation_intelligence", "command": [sys.executable, "-m", "app.platform.conversation_intelligence.conversation_intelligence_check"]},
    {"name": "executive_decision", "command": [sys.executable, "-m", "app.platform.executive_decision.decision_check"]},
    {"name": "v124", "command": [sys.executable, "-m", "app.platform.catalog.x"]},
    {"name": "v125", "command": [sys.executable, "-m", "app.platform.z125"]},
    {"name": "v126", "command": [sys.executable, "-m", "app.platform.f126"]},
    {"name": "v127", "command": [sys.executable, "-m", "app.platform.n127"]},
    {"name": "v128", "command": [sys.executable, "-m", "app.platform.p128"]},
    {"name": "v129", "command": [sys.executable, "-m", "app.platform.o129"]},
    {"name": "v130_134", "command": [sys.executable, "-m", "app.platform.w130_134"]},
    {"name": "v135_139", "command": [sys.executable, "-m", "app.platform.c135_139"]},
    {"name": "v140_144", "command": [sys.executable, "-m", "app.platform.a140_144"]},
    {"name": "v145_149", "command": [sys.executable, "-m", "app.platform.o145_149"]},
    {"name": "v150_153", "command": [sys.executable, "-m", "app.platform.r150_153"]},
    {"name": "v154_157", "command": [sys.executable, "-m", "app.platform.r154_157"]},
    {"name": "v158_160", "command": [sys.executable, "-m", "app.platform.l158_160"]},
    {"name": "d1_1_docker_foundation", "command": [sys.executable, "-m", "app.platform.d1_1"]},
    {"name": "d1_2_postgres_redis", "command": [sys.executable, "-m", "app.platform.d1_2"]},
    {"name": "d1_3_env_secrets", "command": [sys.executable, "-m", "app.platform.d1_3"]},
    {"name": "d1_4_health_readiness", "command": [sys.executable, "-m", "app.platform.d1_4"]},
    {"name": "d1_5_structured_logging", "command": [sys.executable, "-m", "app.platform.deployment.structured_logging_check"]},
    # Clean-up batch 2b (2026-10-16): stale checks fixed (or a real regression fixed) and now run in CI.
    {"name": "auth_boundary_policy", "command": [sys.executable, "-m", "app.platform.auth_boundary.policy_check"]},
    {"name": "board_room_afos_008_regression", "command": [sys.executable, "-m", "app.platform.board_room.afos_008_regression_check"]},
    {"name": "board_room_natural_conversation", "command": [sys.executable, "-m", "app.platform.board_room.natural_conversation_check"]},
    {"name": "operating_console_action_flow", "command": [sys.executable, "-m", "app.platform.operating_console.action_flow_check"]},
    {"name": "ui_jarvis_experience", "command": [sys.executable, "-m", "app.platform.ui.jarvis_experience_check"]},
    {"name": "capability_intelligence", "command": [sys.executable, "-m", "app.platform.capability_intelligence.check"]},
    {"name": "ui_module_size", "command": [sys.executable, "-m", "app.platform.ui.ui_module_size_check"]},
    {"name": "github_execution_mission_identity", "command": [sys.executable, "-m", "app.platform.github_execution.mission_identity_check"], "isolated_db": True},
    {"name": "data_readiness_d35", "command": [sys.executable, "-m", "app.platform.data.readiness.d35_check"]},
    {"name": "persistence_python39_compatibility", "command": [sys.executable, "-m", "app.platform.persistence.python39_compatibility_check"]},
    # Registered by clean-up batch 2 (2026-10-16): checks that existed and passed but never ran in CI.
    {"name": "agents_agent_bridge", "command": [sys.executable, "-m", "app.platform.agents.agent_bridge_check"]},
    {"name": "agents_agent_dependency", "command": [sys.executable, "-m", "app.platform.agents.agent_dependency_check"]},
    {"name": "agents_execution_plan", "command": [sys.executable, "-m", "app.platform.agents.execution_plan_check"]},
    {"name": "agents_filesystem_write_guard", "command": [sys.executable, "-m", "app.platform.agents.filesystem_write_guard_check"]},
    {"name": "agents_lease_safety", "command": [sys.executable, "-m", "app.platform.agents.lease_safety_check"]},
    {"name": "agents_manual_browser_test_harness", "command": [sys.executable, "-m", "app.platform.agents.manual_browser_test_harness_check"]},
    {"name": "agents_materialization_sandbox_writer", "command": [sys.executable, "-m", "app.platform.agents.materialization_sandbox_writer_check"]},
    {"name": "agents_neural_data_fabric_schema", "command": [sys.executable, "-m", "app.platform.agents.neural_data_fabric_schema_check"]},
    {"name": "agents_operator_one_prompt_scoping", "command": [sys.executable, "-m", "app.platform.agents.operator_one_prompt_scoping_check"]},
    {"name": "agents_repair_approval_gate", "command": [sys.executable, "-m", "app.platform.agents.repair_approval_gate_check"]},
    {"name": "agents_repair_plan_generator", "command": [sys.executable, "-m", "app.platform.agents.repair_plan_generator_check"]},
    {"name": "agents_runtime_approval_gate", "command": [sys.executable, "-m", "app.platform.agents.runtime_approval_gate_check"]},
    {"name": "agents_runtime_failure_analyzer", "command": [sys.executable, "-m", "app.platform.agents.runtime_failure_analyzer_check"]},
    {"name": "agents_runtime_readiness_detector", "command": [sys.executable, "-m", "app.platform.agents.runtime_readiness_detector_check"]},
    {"name": "agents_runtime_run_plan_builder", "command": [sys.executable, "-m", "app.platform.agents.runtime_run_plan_builder_check"]},
    {"name": "agents_workflow_execute", "command": [sys.executable, "-m", "app.platform.agents.workflow_execute_check"]},
    {"name": "agents_workflow_runs", "command": [sys.executable, "-m", "app.platform.agents.workflow_runs_check"]},
    {"name": "architecture_agent", "command": [sys.executable, "-m", "app.platform.architecture_agent.check"]},
    {"name": "architecture_agent_sandbox_awareness", "command": [sys.executable, "-m", "app.platform.architecture_agent.sandbox_awareness_check"]},
    {"name": "board_room_afos_009_cognitive", "command": [sys.executable, "-m", "app.platform.board_room.afos_009_cognitive_check"]},
    {"name": "board_room_afos_010_unified_intelligence", "command": [sys.executable, "-m", "app.platform.board_room.afos_010_unified_intelligence_check"]},
    {"name": "board_room", "command": [sys.executable, "-m", "app.platform.board_room.check"]},
    {"name": "board_room_diagnostic_intent_fidelity", "command": [sys.executable, "-m", "app.platform.board_room.diagnostic_intent_fidelity_check"]},
    {"name": "board_room_execution_first_policy", "command": [sys.executable, "-m", "app.platform.board_room.execution_first_policy_check"]},
    {"name": "board_room_executive_context_continuity", "command": [sys.executable, "-m", "app.platform.board_room.executive_context_continuity_check"]},
    {"name": "board_room_executive_decision_engine", "command": [sys.executable, "-m", "app.platform.board_room.executive_decision_engine_check"]},
    {"name": "board_room_intent_fidelity", "command": [sys.executable, "-m", "app.platform.board_room.intent_fidelity_check"]},
    {"name": "company_brain", "command": [sys.executable, "-m", "app.platform.company_brain.check"]},
    {"name": "company_objects", "command": [sys.executable, "-m", "app.platform.company_objects.check"]},
    {"name": "engineering_change_set", "command": [sys.executable, "-m", "app.platform.engineering.change_set_check"]},
    {"name": "events_agent_task_lifecycle_publisher", "command": [sys.executable, "-m", "app.platform.events.agent_task_lifecycle_publisher_check"]},
    {"name": "events_aggregate_knowledge_projection", "command": [sys.executable, "-m", "app.platform.events.aggregate_knowledge_projection_check"]},
    {"name": "events_durable_event_store", "command": [sys.executable, "-m", "app.platform.events.durable_event_store_check"]},
    {"name": "events_governed_event_contract", "command": [sys.executable, "-m", "app.platform.events.governed_event_contract_check"]},
    {"name": "events_mission_lifecycle_publisher", "command": [sys.executable, "-m", "app.platform.events.mission_lifecycle_publisher_check"]},
    {"name": "execution_pr_workflow", "command": [sys.executable, "-m", "app.platform.execution.pr_workflow_check"]},
    {"name": "execution_workflow", "command": [sys.executable, "-m", "app.platform.execution.workflow_check"]},
    {"name": "executive_decision_guided_workflow", "command": [sys.executable, "-m", "app.platform.executive_decision.guided_workflow_check"]},
    {"name": "executive_intelligence_board_room_integration", "command": [sys.executable, "-m", "app.platform.executive_intelligence.board_room_integration_check"]},
    {"name": "executive_intelligence_live_evidence_completion", "command": [sys.executable, "-m", "app.platform.executive_intelligence.live_evidence_completion_check"]},
    {"name": "executive_office", "command": [sys.executable, "-m", "app.platform.executive_office.check"]},
    {"name": "governance_authorization", "command": [sys.executable, "-m", "app.platform.governance_authorization.check"]},
    {"name": "governance_authorization_platform_execution_layer", "command": [sys.executable, "-m", "app.platform.governance_authorization.platform_execution_layer_check"]},
    {"name": "journey_inspection", "command": [sys.executable, "-m", "app.platform.journey_inspection.check"]},
    {"name": "knowledge_vault", "command": [sys.executable, "-m", "app.platform.knowledge_vault.check"]},
    {"name": "mission_control", "command": [sys.executable, "-m", "app.platform.mission_control.check"]},
    {"name": "operating_console_mission_execution_ui", "command": [sys.executable, "-m", "app.platform.operating_console.mission_execution_ui_check"], "isolated_db": True},
    {"name": "operating_console_runtime_inspection", "command": [sys.executable, "-m", "app.platform.operating_console.runtime_inspection_check"]},
    {"name": "operating_console_runtime_reconciliation", "command": [sys.executable, "-m", "app.platform.operating_console.runtime_reconciliation_check"], "isolated_db": True},
    {"name": "organization_console", "command": [sys.executable, "-m", "app.platform.organization_console.check"]},
    {"name": "organization_console_evidence", "command": [sys.executable, "-m", "app.platform.organization_console.evidence_check"]},
    {"name": "organization_console_performance", "command": [sys.executable, "-m", "app.platform.organization_console.performance_check"]},
    {"name": "persistence", "command": [sys.executable, "-m", "app.platform.persistence.check"]},
    {"name": "release_release", "command": [sys.executable, "-m", "app.platform.release.release_check"]},
    {"name": "repository_intelligence", "command": [sys.executable, "-m", "app.platform.repository_intelligence.check"]},
    {"name": "services_board_room_agents_v2", "command": [sys.executable, "-m", "app.platform.services.board_room_agents_v2_check"]},
    {"name": "ui_action_progress", "command": [sys.executable, "-m", "app.platform.ui.action_progress_check"]},
    {"name": "ui_build_identity", "command": [sys.executable, "-m", "app.platform.ui.build_identity_check"]},
    {"name": "ui", "command": [sys.executable, "-m", "app.platform.ui.check"]},
    {"name": "ui_dashboard_script_boundary", "command": [sys.executable, "-m", "app.platform.ui.dashboard_script_boundary_check"]},
    {"name": "validation", "command": [sys.executable, "-m", "app.platform.validation.check"]},
]
PROFILES = ("local", "ci", "production", "artifact", "ai-integration")
ARTIFACT_CHECKS = {
    "frontend_contract",
    "frontend_build",
    "security_report",
    "artifact_registry",
}
AI_INTEGRATION_CHECKS = {"generation_graph", "nautilus_live_smoke", "orca_live_mission"}
# pr-validation.yml's "ci" profile runs on a bare GitHub Actions runner with no
# Chromium installed (unlike the production Dockerfile, which does run
# `playwright install --with-deps chromium`, and a real dev machine, which this
# check was verified against) - a real browser dependency, not something to fake.
# Matches app_build_dashboard_check.py's own precedent of a real Playwright-backed
# check that simply isn't wired into the CI-blocking path.
BROWSER_DEPENDENT_CHECKS = {"ui_ux_agent_preview_registry"}
SMOKE_CHECKS = {
    "platform_routes",
    "login_boundary",
    "d1_4_health_readiness",
}

def check_metadata(item: Dict[str, Any]) -> Dict[str, Any]:
    name = item["name"]
    if name in ARTIFACT_CHECKS:
        return {
            "profiles": ["artifact"],
            "test_type": "generated-artifact regression",
            "requires_cloud": False,
            "requires_secrets": [],
            "mandatory_release_gate": True,
            "applicability": "A generated application workspace must exist.",
        }
    if name in AI_INTEGRATION_CHECKS:
        return {
            "profiles": ["ai-integration"],
            "test_type": "external-service integration",
            "requires_cloud": False,
            "requires_secrets": ["OPENAI_API_KEY"],
            "mandatory_release_gate": True,
            "applicability": "Explicit live AI generation qualification only.",
        }
    if name in BROWSER_DEPENDENT_CHECKS:
        return {
            "profiles": ["local", "production"],
            "test_type": "browser-backed UI regression",
            "requires_cloud": False,
            "requires_secrets": [],
            "mandatory_release_gate": False,
            "applicability": "Requires a real Chromium install (playwright install chromium).",
        }
    return {
        "profiles": ["local", "ci", "production"],
        "test_type": "platform smoke" if name in SMOKE_CHECKS else "platform regression",
        "requires_cloud": False,
        "requires_secrets": [],
        "mandatory_release_gate": True,
        "applicability": "Always applicable to the platform source tree.",
    }


def run_command(name: str, command: List[str], isolated_db: bool = False) -> Dict:
    # "isolated_db" checks wipe shared tables (e.g. every durable mission run) to set up their test,
    # so they always get a fresh temporary platform database, never the configured one.
    if not isolated_db:
        result = subprocess.run(command, capture_output=True, text=True)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, PLATFORM_DATABASE_URL=f"sqlite:///{tmp}/platform.db")
            result = subprocess.run(command, capture_output=True, text=True, env=env)
    return {"name": name, "command": " ".join(command), "return_code": result.returncode, "passed": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr}


def validation_catalogue() -> List[Dict[str, Any]]:
    return [
        dict(
            item,
            **check_metadata(item),
        )
        for item in COMMANDS
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the applicable AI Software Factory validation baseline.")
    parser.add_argument(
        "--profile",
        choices=PROFILES,
        default=os.getenv("VALIDATION_PROFILE", "local"),
        help="Select local, CI, production-reference, generated-artifact, or live AI integration checks.",
    )
    parser.add_argument(
        "--artifact-path",
        help="Generated application workspace to qualify with the artifact profile.",
    )
    parser.add_argument("--list", action="store_true", help="Print the validation architecture catalogue without executing checks.")
    args = parser.parse_args()
    if args.artifact_path:
        os.environ["AFOS_GENERATED_APP_PATH"] = args.artifact_path
    catalogue = validation_catalogue()
    if args.list:
        print(json.dumps({"profiles": list(PROFILES), "checks": catalogue}, indent=2))
        return

    results = []
    for item in catalogue:
        if args.profile not in item["profiles"]:
            results.append(
                {
                    "name": item["name"],
                    "passed": True,
                    "skipped": True,
                    "reason": "Not applicable to the %s validation profile." % args.profile,
                }
            )
            continue
        print(f"Running {item['name']}...")
        result = run_command(name=item["name"], command=item["command"], isolated_db=bool(item.get("isolated_db")))
        result["skipped"] = False
        results.append(result)
        if not result["passed"]:
            print(json.dumps(result, indent=2))
    failed = [result for result in results if not result["passed"]]
    summary = {
        "passed": not failed,
        "profile": args.profile,
        "checks": [
            {
                "name": result["name"],
                "passed": result["passed"],
                "skipped": result.get("skipped", False),
                "return_code": result.get("return_code"),
                "reason": result.get("reason"),
            }
            for result in results
        ],
    }
    print(json.dumps(summary, indent=2))
    if failed:
        print("VALIDATION FAILED")
        raise SystemExit(1)
    print("VALIDATION PASSED")


if __name__ == "__main__":
    main()
