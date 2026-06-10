from __future__ import annotations

from importlib import import_module

_PART_NAMES = ['part_1', 'part_2', 'part_3', 'part_4']
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
