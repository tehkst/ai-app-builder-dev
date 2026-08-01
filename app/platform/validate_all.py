import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, List

COMMANDS = [
    {"name": "compatibility_scanner", "command": [sys.executable, "-m", "app.platform.compatibility.scanner"]},
    {"name": "compatibility_scanner_contract", "command": [sys.executable, "-m", "app.platform.compatibility.scanner_check"]},
    {"name": "validation_architecture", "command": [sys.executable, "-m", "app.platform.validation.architecture_check"]},
    {"name": "dependency_policy", "command": [sys.executable, "-m", "app.platform.compatibility.validate_dependency_policy"]},
    {"name": "platform_routes", "command": [sys.executable, "-m", "app.platform.api.validate_routes"]},
    {"name": "workflow_tracking_engine", "command": [sys.executable, "-m", "app.platform.agents.workflow_tracking_engine_check"]},
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
    {"name": "software_delivery", "command": [sys.executable, "-m", "app.platform.operating_console.afos_013_delivery_check"]},
    {"name": "provider_independent_delivery", "command": [sys.executable, "-m", "app.platform.operating_console.provider_independence_check"]},
    {"name": "artifact_qualification_target", "command": [sys.executable, "-m", "app.platform.artifacts.qualification_target_check"]},
    {"name": "architecture_knowledge_graph", "command": [sys.executable, "-m", "app.platform.architecture_knowledge_graph.check"]},
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
]
PROFILES = ("local", "ci", "production", "artifact", "ai-integration")
ARTIFACT_CHECKS = {
    "frontend_contract",
    "frontend_build",
    "security_report",
    "artifact_registry",
}
AI_INTEGRATION_CHECKS = {"generation_graph"}
SMOKE_CHECKS = {
    "platform_routes",
    "workflow_tracking_engine",
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
    return {
        "profiles": ["local", "ci", "production"],
        "test_type": "platform smoke" if name in SMOKE_CHECKS else "platform regression",
        "requires_cloud": False,
        "requires_secrets": [],
        "mandatory_release_gate": True,
        "applicability": "Always applicable to the platform source tree.",
    }


def run_command(name: str, command: List[str]) -> Dict:
    result = subprocess.run(command, capture_output=True, text=True)
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
        result = run_command(name=item["name"], command=item["command"])
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
