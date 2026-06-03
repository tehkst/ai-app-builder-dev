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
        "name": "frontend_contract",
        "command": [sys.executable, "-m", "app.platform.frontend.validate_frontend_contract"],
    },
    {
        "name": "generation_graph",
        "command": [sys.executable, "test_graph.py"],
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
