from __future__ import annotations

from app.platform.constitution.binder import bind_constitution, constitution_governance_summary
from app.platform.constitution.policy_engine import blocking_rules_for_target, is_allowed_after_validation, rules_for_target
from app.platform.constitution.rules import all_rules
from app.platform.constitution.service import build_constitution_summary
from app.platform.constitution.runtime import get_runtime_constitution


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

    constitution = get_runtime_constitution()
    assert constitution.loaded is True
    assert constitution.version == "KV-0001"
    assert constitution.source == "company/knowledge/KV-0001.md"
    assert constitution.content_hash
    assert constitution.engineering_rules
    assert constitution.approval_rules
    assert constitution.security_rules
    assert constitution.deployment_rules

    summary = build_constitution_summary()
    assert summary["milestone"] == "MC-001"
    assert summary["status"] == "constitution-runtime-loaded"
    assert summary["loaded"] is True
    assert summary["hash"] == constitution.content_hash

    bound = bind_constitution({"request": "test"}, surface="constitution-check")
    assert bound["runtime_constitution"]["version"] == "KV-0001"
    assert bound["constitution_binding"]["status"] == "constitution-bound"

    governance = constitution_governance_summary("test-surface")
    assert governance["approval_policy"]
    assert governance["security_policy"]
    assert governance["engineering_policy"]

    print("CONSTITUTION CHECK PASSED")


if __name__ == "__main__":
    main()
