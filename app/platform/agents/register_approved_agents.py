from __future__ import annotations

import json

from app.platform.agents.builtin import register_builtin_agents
from app.platform.agents.specialists import register_specialist_agents
from app.platform.agents.registry import list_agents
from app.platform.persistence.database import PlatformSessionLocal
from app.platform.services.agent_factory_registration_service import (
    register_approved_specialist_agents,
)


def main() -> None:
    register_builtin_agents()
    register_specialist_agents()

    db = PlatformSessionLocal()
    try:
        result = register_approved_specialist_agents(db)
        result["registered_registry_agents"] = list_agents()
        print(json.dumps(result, indent=2, sort_keys=True))
    finally:
        db.close()


if __name__ == "__main__":
    main()
