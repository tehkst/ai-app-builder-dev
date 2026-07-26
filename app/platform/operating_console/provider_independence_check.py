from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from app.platform.operating_console.delivery_contract import (
    add_artifact,
    create_delivery_contract,
)
from app.platform.runtime.ai_provider import AIProviderError, AIProviderResult
from app.platform.runtime.provider_router import invoke_provider


ROOT = Path(__file__).resolve().parents[3]


def run() -> None:
    calls = []

    def deepseek(**kwargs):
        calls.append(("deepseek", kwargs))
        return AIProviderResult(
            "completed",
            "deepseek",
            kwargs["model"],
            "deepseek-result",
            {"choices": []},
        )

    def openai(**kwargs):
        calls.append(("openai", kwargs))
        return AIProviderResult(
            "completed",
            "openai",
            kwargs["model"],
            "openai-result",
            {"output": []},
        )

    with patch(
        "app.platform.runtime.provider_router.invoke_deepseek",
        side_effect=deepseek,
    ), patch(
        "app.platform.runtime.provider_router.invoke_openai",
        side_effect=openai,
    ):
        deepseek_result = invoke_provider(
            provider="deepseek",
            model="deepseek-v4-pro",
            prompt="bounded mission context",
            system="provider-neutral validation",
        )
        openai_result = invoke_provider(
            provider="openai",
            model="gpt-5.5",
            prompt="bounded mission context",
            system="provider-neutral validation",
        )

    assert [item[0] for item in calls] == ["deepseek", "openai"]
    assert deepseek_result.output_text == "deepseek-result"
    assert openai_result.output_text == "openai-result"
    assert deepseek_result.raw != openai_result.raw

    for provider, model in (
        ("deepseek", "gpt-5.5"),
        ("openai", "deepseek-v4-pro"),
        ("unsupported", "future-model"),
    ):
        try:
            invoke_provider(
                provider=provider,
                model=model,
                prompt="bounded",
                system=None,
            )
        except AIProviderError:
            pass
        else:
            raise AssertionError("Unsupported provider/model selection was accepted.")

    context = {
        "project_id": "PROJECT-AFOS-013",
        "mission_id": "MISSION-AFOS-013",
        "conversation_id": "CONVERSATION-AFOS-013",
        "founder_request": "Build a bounded reference application.",
        "scope": {},
    }
    identities = []
    for provider, model in (
        ("deepseek", "deepseek-v4-pro"),
        ("openai", "gpt-5.5"),
    ):
        provider_context = {**context, "provider": provider, "model": model}
        contract = create_delivery_contract(
            context=provider_context,
            workflow_run_id="MISSION-RUN-AFOS-013",
        )
        artifact = add_artifact(
            contract,
            artifact_type="product_definition",
            authority="planning_service",
            content={"objective": context["founder_request"]},
            source_references=[],
            evidence_references=[],
        )
        identities.append(
            (
                contract["project_identity"],
                contract["mission_identity"],
                contract["workflow_run_identity"],
                artifact["artifact_id"],
                contract["approval_state"],
            )
        )
        assert "api_key" not in str(contract).lower()
    assert identities[0] == identities[1]

    legacy_generation_source = (ROOT / "app/ai/llm.py").read_text(
        encoding="utf-8"
    )
    assert "app.core.llm" not in legacy_generation_source
    assert "from openai" not in legacy_generation_source
    from app.ai.llm import invoke_llm

    with patch(
        "app.ai.llm.invoke_provider",
        return_value=AIProviderResult(
            "completed",
            "deepseek",
            "deepseek-v4-pro",
            "normalized",
            {},
        ),
    ):
        normalized = invoke_llm("bounded provider-neutral generation")
    assert normalized.content == "normalized"
    assert normalized.provider == "deepseek"

    with patch(
        "app.ai.llm.invoke_provider",
        return_value=AIProviderResult(
            "completed",
            "deepseek",
            "deepseek-v4-pro",
            "mission-selected",
            {},
        ),
    ) as routed_generation:
        selected = invoke_llm(
            "bounded provider-neutral generation",
            metadata={
                "provider": "deepseek",
                "model": "deepseek-v4-pro",
            },
        )
    assert selected.content == "mission-selected"
    assert routed_generation.call_args.kwargs["provider"] == "deepseek"
    assert routed_generation.call_args.kwargs["model"] == "deepseek-v4-pro"

    afos_files = (
        "app/platform/operating_console/delivery_contract.py",
        "app/platform/operating_console/mission_run_service.py",
        "app/platform/operating_console/delivery_link.py",
    )
    forbidden = (
        "invoke_openai",
        "invoke_deepseek",
        "ChatOpenAI",
        "OpenAI(",
    )
    for relative_path in afos_files:
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        assert not any(value in source for value in forbidden), relative_path

    browser_source = (
        ROOT / "app/platform/ui/dashboard_browser_script.py"
    ).read_text(encoding="utf-8")
    assert "/mission-control/runtime/ai-provider" in browser_source
    assert "aiProviderSelect" in browser_source
    assert "aiModelInput" in browser_source

    print("AFOS-013 PROVIDER INDEPENDENCE CHECK PASSED")


if __name__ == "__main__":
    run()
