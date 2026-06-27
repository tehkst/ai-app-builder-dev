from __future__ import annotations

from typing import Dict, List

from app.platform.delegation.capability_index import capability_map
from app.platform.runtime.worker import RuntimeWorker


def build_worker_pool() -> Dict[str, RuntimeWorker]:
    workers: Dict[str, RuntimeWorker] = {}
    for capability, agent_ids in capability_map().items():
        for agent_id in agent_ids:
            worker_id = f"worker_{agent_id}"
            existing = workers.get(worker_id)
            capabilities = list(existing.capabilities) if existing else []
            if capability not in capabilities:
                capabilities.append(capability)
            workers[worker_id] = RuntimeWorker(
                worker_id=worker_id,
                agent_id=agent_id,
                capabilities=sorted(capabilities),
                status="available",
                active_job_count=0,
            )
    return workers


def workers_for_capability(required_capability: str) -> List[RuntimeWorker]:
    return [
        worker
        for worker in build_worker_pool().values()
        if worker.status == "available" and required_capability in worker.capabilities
    ]
