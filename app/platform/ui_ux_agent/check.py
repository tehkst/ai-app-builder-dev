from __future__ import annotations

from app.platform.ui_ux_agent.service import (
    _render_and_verify,
    _ui_preview_registry,
    _read_target_file,
    reset_ui_preview_registry_cache,
    resolve_target_file,
)


def main() -> None:
    reset_ui_preview_registry_cache()
    registry = _ui_preview_registry()

    # Both real, currently opted-in pages must be discovered by the AST scan - this
    # was a real, reported gap: only the Board Room chat page had a destination at
    # all, so even a well-formed request to improve the Workflow module's UI had
    # nowhere to go. Confirms the scan itself works, not just that a hardcoded dict
    # happens to list these paths.
    assert "app/platform/ui/founder_dashboard_board_chat.py" in registry
    assert "app/platform/ui/founder_dashboard_stable.py" in registry
    for target_file, declared in registry.items():
        assert declared.get("keywords"), target_file
        assert declared.get("render_function"), target_file

    assert resolve_target_file("make the workflow module more user friendly") == (
        "app/platform/ui/founder_dashboard_stable.py"
    )
    assert resolve_target_file("improve the workflow pipeline layout") == (
        "app/platform/ui/founder_dashboard_stable.py"
    )
    assert resolve_target_file("fix the jarvis chat send button") == (
        "app/platform/ui/founder_dashboard_board_chat.py"
    )
    # A generic UI term with no page named explicitly must still degrade cleanly to
    # "not resolved" rather than silently guessing - the same safety property the
    # single-entry version had, now enforced against a larger, discovered registry.
    assert resolve_target_file("make the customer chat box bigger") is None
    assert resolve_target_file("polish the dashboard") is None

    # The actual preview-render pipeline must work for BOTH targets, not just keyword
    # matching - a registered page with a broken render_function/url_fragment would
    # still "resolve" but silently fail to ever produce a real preview.
    for target_file in (
        "app/platform/ui/founder_dashboard_board_chat.py",
        "app/platform/ui/founder_dashboard_stable.py",
    ):
        content = _read_target_file(target_file)
        assert content, target_file
        result = _render_and_verify(target_file, content, capture_layout_metrics=False)
        assert result.get("status") == "completed", (target_file, result.get("error"))
        assert result.get("screenshot_base64"), target_file

    # A page that never declares UI_UX_PREVIEW_TARGET must never become previewable/
    # proposable - the core safety property: only explicit opt-in, never an arbitrary
    # founder-typed path or a page that merely exists under app/platform/ui/.
    assert "app/platform/ui/mission_control.py" not in registry
    assert resolve_target_file("change mission_control.py directly") is None

    reset_ui_preview_registry_cache()
    assert _ui_preview_registry() == registry, "cache reset should reproduce the identical registry"
    print("UI/UX AGENT PREVIEW REGISTRY CHECK PASSED")


if __name__ == "__main__":
    main()
