"""Runs a recipe in a workspace: agent loop, structured final output and retry-until-checks-pass
(modelled on goose's recipe retry and final_output tool)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.platform.agent_loop.compaction import Summarizer
from app.platform.agent_loop.loop import AgentLoop, AgentLoopConfig, AgentRunResult
from app.platform.agent_loop.messages import ChatFn, user_message
from app.platform.agent_loop.permissions import Approver, Judge, PermissionPolicy
from app.platform.agent_loop.recipe import Recipe
from app.platform.agent_loop.schema_check import schema_errors
from app.platform.agent_loop.tools import Tool, ToolRegistry
from app.platform.agent_loop.workspace_tools import build_workspace_tools, run_workspace_command

CHECK_OUTPUT_CHARS = 4_000
BASE_RULES = (
    "You work inside a single generated-app workspace using the tools provided. Paths are relative "
    "to the workspace root. Never try to modify the AI Software Factory platform itself. Inspect "
    "before you change things, verify your work by running it, and finish with a short summary."
)


@dataclass
class CheckResult:
    command: str
    passed: bool
    exit_code: int
    output: str


@dataclass
class RecipeRunResult:
    status: str  # "succeeded" | "checks_failed" | "missing_output" | "agent_failed"
    attempts: int
    final_text: str
    final_output: Optional[Dict[str, Any]]
    checks: List[CheckResult] = field(default_factory=list)
    runs: List[AgentRunResult] = field(default_factory=list)


def _final_output_tool(schema: Dict[str, Any], sink: Dict[str, Any]) -> Tool:
    def record(arguments: Dict[str, Any]) -> str:
        errors = schema_errors(arguments, schema)
        if errors:
            raise ValueError("final_output does not match the required schema: " + "; ".join(errors))
        sink["value"] = arguments
        return "Final output recorded. Finish now with a one-line confirmation."

    return Tool("final_output", "Submit the task's final structured result. Call exactly once, when done.",
                schema, record, read_only=True)


def run_checks(workspace_root: str, recipe: Recipe) -> List[CheckResult]:
    results = []
    for command in recipe.retry.checks:
        outcome = run_workspace_command(workspace_root, command, recipe.retry.timeout_seconds)
        results.append(CheckResult(command, outcome["exit_code"] == 0, outcome["exit_code"],
                                   outcome["output"][-CHECK_OUTPUT_CHARS:]))
    return results


def _failure_feedback(checks: List[CheckResult]) -> str:
    parts = ["The success checks failed. Fix the problems, then finish again.\n"]
    for check in checks:
        if not check.passed:
            parts.append(f"$ {check.command}\nexit_code: {check.exit_code}\n{check.output}\n")
    return "\n".join(parts)


def run_recipe(recipe: Recipe, *, workspace_root: str, chat: ChatFn, parameters: Optional[Dict[str, Any]] = None,
               approver: Optional[Approver] = None, judge: Optional[Judge] = None,
               summarizer: Optional[Summarizer] = None) -> RecipeRunResult:
    values = recipe.resolve_parameters(parameters or {})
    sink: Dict[str, Any] = {}
    tools = ToolRegistry(build_workspace_tools(workspace_root))
    system = BASE_RULES
    if recipe.instructions:
        system = recipe.render(recipe.instructions, values) + "\n\n" + BASE_RULES
    if recipe.response_schema:
        tools.register(_final_output_tool(recipe.response_schema, sink))
        system += "\nWhen the task is complete, call the final_output tool with the structured result."
    loop = AgentLoop(chat=chat, tools=tools, system_prompt=system, workspace_root=workspace_root,
                     permissions=PermissionPolicy(recipe.permission_mode, approver, judge),
                     summarizer=summarizer, config=AgentLoopConfig(max_turns=recipe.max_turns))

    runs: List[AgentRunResult] = []
    checks: List[CheckResult] = []
    run = loop.run(recipe.render(recipe.prompt, values))
    for attempt in range(1, recipe.retry.max_retries + 2):
        runs.append(run)
        if run.status != "completed":
            return RecipeRunResult("agent_failed", attempt, run.final_text, sink.get("value"), checks, runs)
        feedback = None
        if recipe.response_schema and "value" not in sink:
            feedback = "You finished without calling final_output. Call it now with the structured result."
        else:
            checks = run_checks(workspace_root, recipe)
            if all(check.passed for check in checks):
                return RecipeRunResult("succeeded", attempt, run.final_text, sink.get("value"), checks, runs)
            feedback = _failure_feedback(checks)
            if recipe.retry.on_failure:
                run_workspace_command(workspace_root, recipe.retry.on_failure, recipe.retry.timeout_seconds)
        if attempt > recipe.retry.max_retries:
            status = "missing_output" if recipe.response_schema and "value" not in sink else "checks_failed"
            return RecipeRunResult(status, attempt, run.final_text, sink.get("value"), checks, runs)
        run = loop.resume(run.messages + [user_message(feedback)])
    raise AssertionError("unreachable")  # loop always returns


def describe_result(result: RecipeRunResult) -> str:
    return json.dumps({
        "status": result.status, "attempts": result.attempts, "final_output": result.final_output,
        "checks": [{"command": c.command, "passed": c.passed, "exit_code": c.exit_code} for c in result.checks],
    }, indent=2)
