from __future__ import annotations

import argparse
import json

from app.platform.runtime_stabilization import stabilize_mission_runtime


DEFAULT_MISSION_ID = "MISSION-DA587720B8B6"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Retry one blocked mission through the existing governed change-set runtime."
    )
    parser.add_argument("mission_id", nargs="?", default=DEFAULT_MISSION_ID)
    parser.add_argument("--provider", default=None)
    parser.add_argument("--model", default=None)
    args = parser.parse_args()

    result = stabilize_mission_runtime(
        args.mission_id,
        provider=args.provider,
        model=args.model,
    )
    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    return 0 if result.status == "stable" else 1


if __name__ == "__main__":
    raise SystemExit(main())
