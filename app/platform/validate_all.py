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
