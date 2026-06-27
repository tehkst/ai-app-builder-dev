from __future__ import annotations

from typing import Dict, List

from app.platform.constitution.rules import all_rules


def rules_for_target(target: str) -> Dict[str, Dict[str, object]]:
    return {
        rule_id: rule
        for rule_id, rule in all_rules().items()
        if target in rule.get("targets", [])
    }


def blocking_rules_for_target(target: str) -> List[str]:
    return [
        rule_id
        for rule_id, rule in rules_for_target(target).items()
        if bool(rule.get("blocks_release"))
    ]


def is_allowed_after_validation(target: str) -> bool:
    return bool(rules_for_target(target))
