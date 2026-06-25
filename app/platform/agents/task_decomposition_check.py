from __future__ import annotations

import argparse
import json

from app.platform.engineering.director import draft_scope_from_request
from app.platform.engineering.task_decomposer import v99_task_decomposer_status


def run_task_decomposition_check(request_text: str) -> dict:
    scope_contract = draft_scope_from_request(request_text)
    return {
        "success": scope_contract.is_valid(),
        "version": "v99",
        "scope_contract": scope_contract.to_dict(),
        "task_decomposer": v99_task_decomposer_status(),
        "task_graph_generated": False,
        "reason": "V99 placeholder check confirms scope contract is valid before dynamic task graph generation is connected.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run V99 task decomposition readiness check.")
    parser.add_argument("request_text")
    args = parser.parse_args()
    print(json.dumps(run_task_decomposition_check(args.request_text), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
