import json
import subprocess


MAX_LIST_LIMIT = 100
COMMAND_TIMEOUT_SECONDS = 300


def extract_json_block(stdout: str):
    start = stdout.find("{")
    end = stdout.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(stdout[start : end + 1])
    except json.JSONDecodeError:
        return None


def run_platform_command(command: list, timeout: int = COMMAND_TIMEOUT_SECONDS) -> dict:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        return {
            "passed": result.returncode == 0,
            "return_code": result.returncode,
            "command": " ".join(command),
            "parsed_output": extract_json_block(result.stdout),
            "stdout": result.stdout,
            "stderr": result.stderr if result.returncode != 0 else "",
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as error:
        return {
            "passed": False,
            "return_code": None,
            "command": " ".join(command),
            "parsed_output": None,
            "stdout": error.stdout or "",
            "stderr": error.stderr or "",
            "timed_out": True,
            "timeout_seconds": timeout,
        }


def clamp_limit(limit: int) -> int:
    if limit < 1:
        return 1
    if limit > MAX_LIST_LIMIT:
        return MAX_LIST_LIMIT
    return limit
