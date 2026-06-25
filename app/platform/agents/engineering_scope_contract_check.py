from __future__ import annotations

import argparse
import json

from app.platform.engineering.director import classify_engineering_request, draft_scope_from_request


def run_engineering_scope_contract_check(request_text: str) -> dict:
    classification = classify_engineering_request(request_text)
    scope_contract = draft_scope_from_request(request_text)
    return {
        "success": scope_contract.is_valid(),
        "classification": classification.to_dict(),
        "scope_contract": scope_contract.to_dict(),
        "scope_before_build_enforced": True,
        "build_started": False,
        "materialization_performed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Draft and validate a V98 engineering scope contract.")
    parser.add_argument("request_text", help="Engineering request to classify and scope before build.")
    args = parser.parse_args()
    result = run_engineering_scope_contract_check(args.request_text)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
