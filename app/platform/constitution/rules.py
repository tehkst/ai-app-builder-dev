from __future__ import annotations

from typing import Dict


RULES: Dict[str, Dict[str, object]] = {
    "scope_before_build": {
        "category": "planning",
        "severity": "critical",
        "targets": ["workflow", "agent", "runtime"],
        "blocks_release": True,
    },
    "validation_required": {
        "category": "quality",
        "severity": "critical",
        "targets": ["merge", "release", "deployment"],
        "blocks_release": True,
    },
    "small_modular_files": {
        "category": "modularity",
        "severity": "warning",
        "targets": ["code", "review"],
        "blocks_release": False,
    },
    "controlled_runtime_only": {
        "category": "runtime",
        "severity": "critical",
        "targets": ["runtime", "deployment"],
        "blocks_release": True,
    },
}


def all_rules() -> Dict[str, Dict[str, object]]:
    return dict(RULES)
