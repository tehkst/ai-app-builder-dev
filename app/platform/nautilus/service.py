"""Entry points that wire the agent loop to the platform's configured AI provider."""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.platform.nautilus.chat_providers import build_chat_fn
from app.platform.nautilus.compaction import Summarizer
from app.platform.nautilus.loop import AgentLoop, AgentLoopConfig, AgentRunResult
from app.platform.nautilus.permissions import Approver, Judge, PermissionPolicy, build_llm_judge
from app.platform.nautilus.recipe import load_recipe
from app.platform.nautilus.recipe_runner import BASE_RULES, RecipeRunResult, run_recipe
from app.platform.nautilus.tools import ToolRegistry
from app.platform.nautilus.workspace_tools import build_workspace_tools


def _complete(system: str, prompt: str, provider: Optional[str], model: Optional[str]) -> str:
    from app.platform.runtime.provider_router import invoke_provider

    result = invoke_provider(provider=provider, prompt=prompt, system=system, model=model)
    if result.status != "completed":
        raise RuntimeError(f"AI provider returned status '{result.status}'.")
    return result.output_text


def build_summarizer(provider: Optional[str] = None, model: Optional[str] = None) -> Summarizer:
    return lambda prompt: _complete("You write faithful, concise working summaries.", prompt, provider, model)


def build_provider_judge(provider: Optional[str] = None, model: Optional[str] = None) -> Judge:
    return build_llm_judge(lambda system, prompt: _complete(system, prompt, provider, model))


def run_workspace_agent(goal: str, *, workspace_root: str, system_prompt: str = BASE_RULES,
                        permission_mode: str = "approve", approver: Optional[Approver] = None,
                        use_llm_judge: bool = False, provider: Optional[str] = None,
                        model: Optional[str] = None, max_turns: int = 25) -> AgentRunResult:
    """Run one tool-using agent against a generated-app workspace.

    Defaults are conservative: ``approve`` mode with no approver means the agent can read
    and inspect but every write or command is denied until a caller supplies an approver.
    """
    loop = AgentLoop(
        chat=build_chat_fn(provider, model),
        tools=ToolRegistry(build_workspace_tools(workspace_root)),
        system_prompt=system_prompt,
        permissions=PermissionPolicy(permission_mode, approver,
                                     build_provider_judge(provider, model) if use_llm_judge else None),
        workspace_root=workspace_root,
        summarizer=build_summarizer(provider, model),
        config=AgentLoopConfig(max_turns=max_turns),
    )
    return loop.run(goal)


def run_recipe_file(path: str, *, workspace_root: str, parameters: Optional[Dict[str, Any]] = None,
                    approver: Optional[Approver] = None, use_llm_judge: bool = False,
                    provider: Optional[str] = None, model: Optional[str] = None) -> RecipeRunResult:
    return run_recipe(
        load_recipe(path), workspace_root=workspace_root, chat=build_chat_fn(provider, model),
        parameters=parameters, approver=approver,
        judge=build_provider_judge(provider, model) if use_llm_judge else None,
        summarizer=build_summarizer(provider, model),
    )
