"""Live smoke test: Nautilus against the real configured AI provider.

Needs a real API key (DEEPSEEK_API_KEY or OPENAI_API_KEY via the credential vault or the
environment), so it runs in the ai-integration validation profile and in CI with the
repository secret - never in the keyless local/ci profiles. Costs a few cents per run.

    AI_PROVIDER=deepseek python -m app.platform.nautilus.live_smoke_check
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from app.platform.nautilus.recipe import recipe_from_dict
from app.platform.nautilus.recipe_runner import describe_result, run_recipe
from app.platform.nautilus.chat_providers import build_chat_fn
from app.platform.nautilus.service import run_workspace_agent
from app.platform.runtime.provider_router import default_model, provider_status, selected_provider

SMOKE_TURNS = 8


def _require_key() -> str:
    from app.platform.persistence.database import create_platform_tables

    create_platform_tables()  # provider selection reads the runtime settings table
    status = provider_status()
    if not status["api_key_present"]:
        print(f"NAUTILUS LIVE SMOKE FAILED: {status['secret_name']} is not configured for provider "
              f"'{status['provider']}'.")
        sys.exit(1)
    return status["provider"]


def check_tool_loop(provider: str, model: str) -> None:
    with tempfile.TemporaryDirectory() as root:
        (Path(root) / "notes.txt").write_text("The secret word is: chambered\n")
        result = run_workspace_agent(
            "Read notes.txt, then create answer.txt containing only the secret word from it "
            "(lowercase, no other text). Then reply with the single word DONE.",
            workspace_root=root, permission_mode="auto", provider=provider, model=model, max_turns=SMOKE_TURNS,
        )
        names = [record.name for record in result.tool_calls]
        print(f"  tool loop: status={result.status} turns={result.turns} calls={names}")
        assert result.status == "completed", (result.status, result.error, result.final_text)
        assert "read_file" in names and "write_file" in names, names
        answer = (Path(root) / "answer.txt").read_text().strip().lower()
        assert answer == "chambered", answer


def check_recipe(provider: str, model: str) -> None:
    recipe = recipe_from_dict({
        "title": "Live smoke recipe",
        "description": "Writes a file the success check verifies, and returns structured output.",
        "prompt": "Create status.txt containing exactly the text: {{ word }}",
        "parameters": [{"key": "word", "requirement": "required"}],
        "permission_mode": "auto",
        "max_turns": SMOKE_TURNS,
        "response": {"json_schema": {"type": "object", "required": ["files_written"],
                                     "properties": {"files_written": {"type": "array", "items": {"type": "string"}}}}},
        "retry": {"max_retries": 1, "checks": ["grep -qx nautilus-ok status.txt"]},
    })
    with tempfile.TemporaryDirectory() as root:
        result = run_recipe(recipe, workspace_root=root, chat=build_chat_fn(provider, model),
                            parameters={"word": "nautilus-ok"})
        print("  recipe: " + describe_result(result).replace("\n", " "))
        assert result.status == "succeeded", describe_result(result)
        assert "status.txt" in " ".join(result.final_output["files_written"]), result.final_output


def main() -> None:
    provider = _require_key()
    model = os.getenv("NAUTILUS_SMOKE_MODEL") or default_model(selected_provider(provider))
    print(f"Nautilus live smoke test: provider={provider} model={model}")
    check_tool_loop(provider, model)
    check_recipe(provider, model)
    print("NAUTILUS LIVE SMOKE PASSED")


if __name__ == "__main__":
    main()
