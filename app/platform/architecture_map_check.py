"""Fails when the architecture map and the code drift apart (clean-up batch 5).

Every top-level area of app/ must be in architecture_map.MAP with a known layer and status, every
MAP entry must still exist, and docs/architecture/MODULE_MAP.md must equal the rendered map.
Fix by editing app/platform/architecture_map.py and running
`python -m app.platform.architecture_map --write`.
"""
from __future__ import annotations

from app.platform.architecture_map import DOC_PATH, LAYERS, MAP, STATUS_ORDER, discover, render_markdown


def main() -> None:
    on_disk = discover()
    missing = sorted(on_disk - set(MAP))
    stale = sorted(set(MAP) - on_disk)
    assert not missing, f"Add these areas to app/platform/architecture_map.py: {missing}"
    assert not stale, f"Remove these areas (no longer on disk) from the map: {stale}"
    layers = {key for key, _, _ in LAYERS}
    bad = {name: info for name, info in MAP.items() if info[0] not in layers or info[1] not in STATUS_ORDER or not info[2]}
    assert not bad, f"Unknown layer/status or empty description: {bad}"
    assert DOC_PATH.exists() and DOC_PATH.read_text(encoding="utf-8") == render_markdown(), (
        "docs/architecture/MODULE_MAP.md is out of date: run python -m app.platform.architecture_map --write")
    print(f"ARCHITECTURE MAP CHECK PASSED ({len(MAP)} areas)")


if __name__ == "__main__":
    main()
