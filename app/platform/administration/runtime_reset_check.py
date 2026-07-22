from __future__ import annotations

from app.platform.administration.runtime_reset import (
    CONFIRMATION_PHRASE,
    RuntimeResetRegistry,
)


def _handler(state: dict[str, int], key: str, *, fail: bool = False):
    def preview():
        return {"records": state[key]}

    def execute():
        if fail:
            raise RuntimeError("simulated failure")
        cleared = state[key]
        state[key] = 0
        return {"status": "cleared" if cleared else "already-clean", "cleared": cleared}

    def verify():
        return {"remaining": state[key]}

    return preview, execute, verify


def main() -> None:
    registry = RuntimeResetRegistry()
    state = {
        "missions": 1,
        "planning": 2,
        "executive_inbox": 1,
        "board_room": 1,
        "jarvis_conversations": 3,
        "workflow_runtime": 2,
        "github_cache": 1,
        "deployment_evidence": 1,
        "agent_sessions": 2,
        "mission_memory": 1,
    }
    for key in state:
        preview, execute, verify = _handler(state, key)
        registry.register(key, preview=preview, execute=execute, verify=verify)

    preview = registry.preview()
    assert preview["status"] == "preview-ready"
    assert preview["external_systems_touched"] is False
    assert sum(int(item.get("records") or 0) for item in preview["clear"]) == 15

    blocked = registry.execute({})
    assert blocked["status"] == "blocked"

    wrong_phrase = registry.execute({
        "authorization_status": "approved",
        "preview_acknowledged": True,
        "confirmation": "wrong",
    })
    assert wrong_phrase["status"] == "blocked"

    result = registry.execute({
        "authorization_status": "approved",
        "preview_acknowledged": True,
        "confirmation": CONFIRMATION_PHRASE,
    })
    assert result["status"] == "reset-complete"
    assert result["verification"]["clean"] is True
    assert result["external_systems_touched"] is False

    repeated = registry.execute({
        "authorization_status": "approved",
        "preview_acknowledged": True,
        "confirmation": CONFIRMATION_PHRASE,
    })
    assert repeated["status"] == "reset-complete"
    assert all(item["cleared"] == 0 for item in repeated["results"])

    partial = RuntimeResetRegistry()
    failed_state = dict(state)
    for key in failed_state:
        preview, execute, verify = _handler(failed_state, key, fail=key == "missions")
        partial.register(key, preview=preview, execute=execute, verify=verify)
    failed_state["missions"] = 1
    partial_result = partial.execute({
        "authorization_status": "approved",
        "preview_acknowledged": True,
        "confirmation": CONFIRMATION_PHRASE,
    })
    assert partial_result["status"] == "partial-failure"
    assert partial_result["verification"]["clean"] is False

    print("runtime reset checks passed")


if __name__ == "__main__":
    main()
