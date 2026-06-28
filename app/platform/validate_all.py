import json
import subprocess
import sys
from typing import Dict, List


COMMANDS = [
    {
        "name": "compatibility_scanner",
        "command": [sys.executable, "-m", "app.platform.compatibility.scanner"],
    },
    {
        "name": "dependency_policy",
        "command": [sys.executable, "-m", "app.platform.compatibility.validate_dependency_policy"],
    },
    {
        "name": "platform_routes",
        "command": [sys.executable, "-m", "app.platform.api.validate_routes"],
    },
    {
        "name": "workflow_tracking_engine",
        "command": [sys.executable, "-m", "app.platform.agents.workflow_tracking_engine_check"],
    },
    {
        "name": "frontend_contract",
        "command": [sys.executable, "-m", "app.platform.frontend.validate_frontend_contract"],
    },
    {
        "name": "frontend_build",
        "command": [sys.executable, "-m", "app.platform.frontend.validate_frontend_build"],
    },
    {
        "name": "security_report",
        "command": [sys.executable, "-m", "app.platform.security_report"],
    },
    {
        "name": "generation_graph",
        "command": [sys.executable, "test_graph.py"],
    },
    {
        "name": "artifact_registry",
        "command": [sys.executable, "-m", "app.platform.artifacts.registry_report"],
    },
    {
        "name": "v100_workflow",
        "command": [sys.executable, "-m", "app.platform.agents.v100_workflow_check"],
    },
    {
        "name": "agent_manifest",
        "command": [sys.executable, "-m", "app.platform.agents.manifest_check"],
    },
    {
        "name": "agent_manifest_sync",
        "command": [sys.executable, "-m", "app.platform.agents.manifest_registry_sync_check"],
    },
    {
        "name": "organization_hierarchy",
        "command": [sys.executable, "-m", "app.platform.organization.organization_check"],
    },
    {
        "name": "engineering_memory",
        "command": [sys.executable, "-m", "app.platform.memory.memory_check"],
    },
    {
        "name": "engineering_knowledge_graph",
        "command": [sys.executable, "-m", "app.platform.knowledge.knowledge_check"],
    },
    {
        "name": "engineering_management",
        "command": [sys.executable, "-m", "app.platform.management.management_check"],
    },
    {
        "name": "pmo",
        "command": [sys.executable, "-m", "app.platform.pmo.pmo_check"],
    },
    {
        "name": "pmo_planning",
        "command": [sys.executable, "-m", "app.platform.pmo.planning_check"],
    },
    {
        "name": "pmo_graph",
        "command": [sys.executable, "-m", "app.platform.pmo.graph_check"],
    },
    {
        "name": "constitution",
        "command": [sys.executable, "-m", "app.platform.constitution.constitution_check"],
    },
    {
        "name": "delegation",
        "command": [sys.executable, "-m", "app.platform.delegation.delegation_check"],
    },
    {
        "name": "delegation_scheduler",
        "command": [sys.executable, "-m", "app.platform.delegation.scheduler_check"],
    },
    {
        "name": "delegation_manager",
        "command": [sys.executable, "-m", "app.platform.delegation.manager_check"],
    },
    {
        "name": "runtime",
        "command": [sys.executable, "-m", "app.platform.runtime.check_runtime"],
    },
    {
        "name": "runtime_engine",
        "command": [sys.executable, "-m", "app.platform.runtime.runtime_engine_check"],
    },
    {
        "name": "runtime_recovery",
        "command": [sys.executable, "-m", "app.platform.runtime.runtime_recovery_check"],
    },
    {
        "name": "event_bus",
        "command": [sys.executable, "-m", "app.platform.events.event_check"],
    },
    {
        "name": "self_healing",
        "command": [sys.executable, "-m", "app.platform.self_healing.self_healing_check"],
    },
    {
        "name": "plugin_architecture",
        "command": [sys.executable, "-m", "app.platform.plugins.plugin_check"],
    },
    {
        "name": "decision_intelligence",
        "command": [sys.executable, "-m", "app.platform.learning.learning_check"],
    },
    {
        "name": "platform_registry",
        "command": [sys.executable, "-m", "app.platform.registry.registry_check"],
    },
    {
        "name": "deployment_platform",
        "command": [sys.executable, "-m", "app.platform.deployment.deployment_check"],
    },
    {
        "name": "operations_center",
        "command": [sys.executable, "-m", "app.platform.operations.operations_check"],
    },
    {
        "name": "admin_console",
        "command": [sys.executable, "-m", "app.platform.webconsole.console_check"],
    },
    {
        "name": "api_gateway",
        "command": [sys.executable, "-m", "app.platform.api_gateway.gateway_check"],
    },
    {
        "name": "auth_foundation",
        "command": [sys.executable, "-m", "app.platform.auth.auth_check"],
    },
    {
        "name": "saas_portal",
        "command": [sys.executable, "-m", "app.platform.saas_portal.portal_check"],
    },
    {
        "name": "platform_integration",
        "command": [sys.executable, "-m", "app.platform.integration.integration_check"],
    },
    {
        "name": "application_lifecycle",
        "command": [sys.executable, "-m", "app.platform.lifecycle.lifecycle_check"],
    },
    {
        "name": "subscription_management",
        "command": [sys.executable, "-m", "app.platform.billing.billing_check"],
    },
]


def run_command(name: str, command: List[str]) -> Dict:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    return {
        "name": name,
        "command": " ".join(command),
        "return_code": result.returncode,
        "passed": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def main() -> None:
    results = []

    for item in COMMANDS:
        print(f"Running {item['name']}...")
        result = run_command(
            name=item["name"],
            command=item["command"],
        )
        results.append(result)

        if not result["passed"]:
            print(json.dumps(result, indent=2))
            print("VALIDATION FAILED")
            raise SystemExit(1)

    summary = {
        "passed": True,
        "checks": [
            {
                "name": result["name"],
                "passed": result["passed"],
                "return_code": result["return_code"],
            }
            for result in results
        ],
    }

    print(json.dumps(summary, indent=2))
    print("VALIDATION PASSED")


if __name__ == "__main__":
    main()
