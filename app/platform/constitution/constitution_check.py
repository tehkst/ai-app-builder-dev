from __future__ import annotations

from app.platform.constitution.policy_engine import blocking_rules_for_target, is_allowed_after_validation, rules_for_target
from app.platform.constitution.rules import all_rules


REQUIRED_RULES = {
    "scope_before_build",
    "validation_required",
    "small_modular_files",
    "controlled_runtime_only",
}


def main() -> None:
    rules = all_rules()

    assert REQUIRED_RULES.issubset(set(rules)), rules

    for rule_id, rule in rules.items():
        assert rule_id, rule
        assert rule.get("category"), rule
        assert rule.get("severity") in {"critical", "warning", "info"}, rule
        assert rule.get("targets"), rule
        assert isinstance(rule.get("blocks_release"), bool), rule

    assert "validation_required" in blocking_rules_for_target("merge")
    assert "controlled_runtime_only" in blocking_rules_for_target("runtime")
    assert rules_for_target("code")
    assert is_allowed_after_validation("merge") is True

    print("CONSTITUTION CHECK PASSED")


if __name__ == "__main__":
    main()
