from __future__ import annotations

import argparse
import json

from app.platform.services.app_build_workflow_generator_service import (
    generate_app_build_workflow,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a safe app-build workflow from a user app request."
    )
    parser.add_argument(
        "app_request",
        help="User app request, for example: 'Build me a booking app for yoga classes'.",
    )
    parser.add_argument(
        "--workflow-name",
        help="Optional workflow name override.",
    )
    args = parser.parse_args()

    result = generate_app_build_workflow(
        app_request=args.app_request,
        workflow_name=args.workflow_name,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
