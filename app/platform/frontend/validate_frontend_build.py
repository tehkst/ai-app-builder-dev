import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FRONTEND_DIR = ROOT / "generated_apps" / "crm-saas-multifile-001" / "frontend"


def main() -> None:
    package_json = FRONTEND_DIR / "package.json"
    node_modules = FRONTEND_DIR / "node_modules"

    if not package_json.exists():
        result = {
            "passed": False,
            "skipped": False,
            "reason": "frontend package.json not found",
            "frontend_dir": str(FRONTEND_DIR),
        }
        print(json.dumps(result, indent=2))
        raise SystemExit(1)

    if not node_modules.exists():
        result = {
            "passed": True,
            "skipped": True,
            "reason": "node_modules not found; run npm install in generated frontend to enable build validation",
            "frontend_dir": str(FRONTEND_DIR),
        }
        print(json.dumps(result, indent=2))
        return

    command = ["npm", "run", "build"]

    completed = subprocess.run(
        command,
        cwd=FRONTEND_DIR,
        capture_output=True,
        text=True,
    )

    result = {
        "passed": completed.returncode == 0,
        "skipped": False,
        "command": " ".join(command),
        "frontend_dir": str(FRONTEND_DIR),
        "return_code": completed.returncode,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }

    print(json.dumps(result, indent=2))

    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
