from __future__ import annotations

from importlib import import_module

_PART_NAMES = ['part_1', 'part_2', 'part_3']
_MODULES = [import_module(f"{__name__}.{part_name}") for part_name in _PART_NAMES]

_SHARED_NAMES = {}
for _module in _MODULES:
    for _name, _value in vars(_module).items():
        if _name.startswith("__"):
            continue
        _SHARED_NAMES[_name] = _value

for _module in _MODULES:
    vars(_module).update(_SHARED_NAMES)

globals().update(_SHARED_NAMES)
__all__ = sorted(name for name in _SHARED_NAMES if not name.startswith("_"))

# The original, pre-split specialists.py had a bare register_specialist_agents()
# call at module level - several real call sites (organization_console/service.py,
# agents/worker.py, agents/run_project/, manifest_registry_sync_check.py,
# organization_check.py, management_check.py) do `import
# app.platform.agents.specialists  # noqa: F401` specifically to trigger that
# side effect, never calling register_specialist_agents() themselves. Preserving
# it here - dropping it during the part_1/part_2/part_3 split was a real
# regression, caught by a live CI failure on this exact PR.
register_specialist_agents()
