"""Deterministic check for recipes and the provider wire-format adapters (no network)."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.platform.nautilus.loop_check import call, scripted, turn
from app.platform.nautilus.chat_providers import (
    OPENAI_ITEMS_KEY, parse_deepseek_response, parse_openai_response, to_openai_input,
)
from app.platform.nautilus.recipe import RecipeError, load_recipe, recipe_from_dict
from app.platform.nautilus.recipe_runner import run_recipe
from app.platform.nautilus.schema_check import schema_errors

RECIPE_YAML = """
title: Create greeting
description: Writes a greeting file for an app
instructions: You are building {{ app_name }}.
prompt: Create greeting.txt containing "hello {{ app_name }}".
parameters:
  - {key: app_name, requirement: required}
  - {key: tone, requirement: optional, default: friendly}
permission_mode: auto
response:
  json_schema:
    type: object
    required: [summary, files]
    properties:
      summary: {type: string}
      files: {type: array, items: {type: string}}
retry:
  max_retries: 1
  checks:
    - {type: shell, command: "grep -q 'hello acme' greeting.txt"}
"""


def check_recipe_loading(root: str) -> None:
    path = Path(root) / "greet.yaml"
    path.write_text(RECIPE_YAML)
    recipe = load_recipe(str(path))
    assert recipe.permission_mode == "auto" and recipe.retry.max_retries == 1, recipe
    values = recipe.resolve_parameters({"app_name": "acme"})
    assert values == {"app_name": "acme", "tone": "friendly"}, values
    assert recipe.render(recipe.prompt, values) == 'Create greeting.txt containing "hello acme".'
    for bad, message in (({}, "missing required"), ):
        try:
            recipe.resolve_parameters(bad)
            raise AssertionError("expected RecipeError")
        except RecipeError as exc:
            assert message in str(exc), exc
    for broken in ({"title": "t", "description": "d"}, {"title": "t", "description": "d", "prompt": "p",
                                                         "permission_mode": "yolo"}):
        try:
            recipe_from_dict(broken)
            raise AssertionError(f"expected RecipeError for {broken}")
        except RecipeError:
            pass
    errors = schema_errors({"summary": 1}, recipe.response_schema)
    assert sorted(errors) == ["$.files is required", "$.summary should be string"], errors


def check_retry_until_checks_pass(root: str) -> None:
    recipe = load_recipe(str(Path(root) / "greet.yaml"))
    good_output = {"summary": "wrote greeting", "files": ["greeting.txt"]}
    chat = scripted(
        turn("", [call("w1", "write_file", path="greeting.txt", content="hi acme")]),  # wrong content
        turn("", [call("f1", "final_output", **good_output)]),
        turn("Done."),
        turn("", [call("w2", "write_file", path="greeting.txt", content="hello acme")]),  # after check feedback
        turn("Fixed."),
    )
    result = run_recipe(recipe, workspace_root=root, chat=chat, parameters={"app_name": "acme"})
    assert result.status == "succeeded" and result.attempts == 2, (result.status, result.attempts)
    assert result.final_output == good_output and all(c.passed for c in result.checks), result
    feedback = [m for m in chat.seen[3] if m["role"] == "user"][-1]["content"]
    assert "success checks failed" in feedback and "grep -q" in feedback, feedback
    assert chat.seen[0][0]["content"].startswith("You are building acme."), chat.seen[0][0]

    (Path(root) / "greeting.txt").unlink()
    never = scripted(*[turn("", [call(f"n{i}", "final_output", **good_output)]) if i % 2 == 0 else turn("done")
                       for i in range(6)])
    failed = run_recipe(recipe, workspace_root=root, chat=never, parameters={"app_name": "acme"})
    assert failed.status == "checks_failed" and failed.attempts == 2, (failed.status, failed.attempts)

    invalid = scripted(turn("", [call("f", "final_output", summary=3)]), turn("done"), turn("still done"),
                       turn("done again"))
    missing = run_recipe(recipe, workspace_root=root, chat=invalid, parameters={"app_name": "acme"})
    assert missing.status == "missing_output", missing.status
    assert missing.runs[0].tool_calls[0].outcome == "error", missing.runs[0].tool_calls


def check_openai_format() -> None:
    raw = {"output": [
        {"type": "reasoning", "id": "rs_1", "summary": []},
        {"type": "function_call", "id": "fc_1", "call_id": "call_9", "name": "read_file", "arguments": "{\"path\": \"a\"}"},
    ], "usage": {"total_tokens": 10}}
    reply = parse_openai_response(raw, "gpt-5.5")
    assert reply.tool_calls[0].call_id == "call_9" and reply.tool_calls[0].arguments == {"path": "a"}, reply
    items = to_openai_input([{"role": "system", "content": "s"}, {"role": "user", "content": "u"},
                             reply.assistant_message, {"role": "tool", "tool_call_id": "call_9", "content": "data"}])
    assert [i.get("type") or i.get("role") for i in items] == ["system", "user", "reasoning", "function_call",
                                                               "function_call_output"], items
    plain = to_openai_input([{"role": "assistant", "content": "x", "tool_calls": [
        {"id": "c1", "type": "function", "function": {"name": "n", "arguments": "{}"}}]}])
    assert plain[1] == {"type": "function_call", "call_id": "c1", "name": "n", "arguments": "{}"}, plain
    text = parse_openai_response({"output": [{"type": "message", "content": [{"type": "output_text", "text": "hi"}]}]}, "m")
    assert text.text == "hi" and not text.tool_calls, text


def check_deepseek_format() -> None:
    raw = {"choices": [{"message": {"role": "assistant", "content": None, "reasoning_content": "think",
                                    "tool_calls": [{"id": "d1", "type": "function",
                                                    "function": {"name": "list_files", "arguments": "{}"}}]}}]}
    reply = parse_deepseek_response(raw, "deepseek-v4-pro")
    assert reply.tool_calls[0].name == "list_files" and reply.text == "", reply
    assert "content" not in reply.assistant_message and reply.assistant_message["reasoning_content"] == "think"
    assert OPENAI_ITEMS_KEY not in json.dumps(reply.assistant_message)


def main() -> None:
    with tempfile.TemporaryDirectory() as root:
        check_recipe_loading(root)
        check_retry_until_checks_pass(root)
    check_openai_format()
    check_deepseek_format()
    print("NAUTILUS RECIPE CHECK PASSED")


if __name__ == "__main__":
    main()
