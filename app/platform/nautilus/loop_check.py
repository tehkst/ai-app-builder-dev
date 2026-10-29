"""Deterministic check for the agent loop (no network, no API keys): a scripted chat
function stands in for the model."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict, List

from app.platform.nautilus.compaction import compact_messages, needs_compaction
from app.platform.nautilus.loop import AgentLoop, AgentLoopConfig
from app.platform.nautilus.messages import ChatTurn, ToolCall
from app.platform.nautilus.permissions import PermissionPolicy, command_is_read_only
from app.platform.nautilus.tools import Tool, ToolRegistry, object_schema
from app.platform.nautilus.workspace_tools import build_workspace_tools


def turn(text: str = "", calls: List[ToolCall] = ()) -> ChatTurn:
    assistant: Dict[str, Any] = {"role": "assistant", "content": text}
    if calls:
        assistant["tool_calls"] = [{"id": c.call_id, "type": "function",
                                    "function": {"name": c.name, "arguments": c.raw_arguments}} for c in calls]
    return ChatTurn(text, list(calls), assistant)


def call(call_id: str, name: str, **arguments: Any) -> ToolCall:
    import json

    return ToolCall(call_id, name, arguments, json.dumps(arguments))


def scripted(*turns: ChatTurn):
    queue = list(turns)
    seen: List[List[Dict[str, Any]]] = []

    def chat(messages, tools):
        seen.append(list(messages))
        return queue.pop(0) if queue else turn("done")

    chat.seen = seen
    return chat


def check_write_run_and_finish(root: str) -> None:
    chat = scripted(
        turn("", [call("c1", "write_file", path="app/hello.py", content="print('hi')\n")]),
        turn("", [call("c2", "run_command", command="python3 app/hello.py"), call("c3", "list_files")]),
        turn("Created app/hello.py and ran it."),
    )
    loop = AgentLoop(chat=chat, tools=ToolRegistry(build_workspace_tools(root)), system_prompt="sys",
                     permissions=PermissionPolicy("auto"), workspace_root=root)
    result = loop.run("make hello")
    assert result.status == "completed", result
    assert result.turns == 3 and [r.outcome for r in result.tool_calls] == ["ok", "ok", "ok"], result.tool_calls
    assert (Path(root) / "app/hello.py").read_text() == "print('hi')\n"
    tool_results = [m["content"] for m in result.messages if m["role"] == "tool"]
    assert "exit_code: 0" in tool_results[1] and "hi" in tool_results[1], tool_results
    assert "app/hello.py" in tool_results[2], tool_results


def check_permissions_and_sandbox(root: str) -> None:
    chat = scripted(
        turn("", [call("p1", "write_file", path="x.txt", content="x"), call("p2", "read_file", path="../escape.txt"),
                  call("p3", "run_command", command="ls"), call("p4", "run_command", command="rm -rf app")]),
        turn("stopping"),
    )
    loop = AgentLoop(chat=chat, tools=ToolRegistry(build_workspace_tools(root)), system_prompt="sys",
                     permissions=PermissionPolicy("smart"), workspace_root=root)
    outcomes = [r.outcome for r in loop.run("try things").tool_calls]
    assert outcomes == ["denied", "error", "ok", "denied"], outcomes
    assert not (Path(root) / "x.txt").exists() and (Path(root) / "app").exists()
    approved = PermissionPolicy("approve", approver=lambda c: c.name == "write_file")
    tools = ToolRegistry(build_workspace_tools(root))
    assert approved.decide(tools.get("write_file"), call("a", "write_file", path="y", content="")).allowed
    assert not approved.decide(tools.get("run_command"), call("b", "run_command", command="ls")).allowed
    assert command_is_read_only("git status") and command_is_read_only("find . -name '*.py'")
    assert command_is_read_only("cat app/main.py", root) and command_is_read_only("grep -rn TODO app", root)
    for unsafe in ("git branch -D main", "find . -delete", "git diff --output=x", "python3 x.py", "rm a",
                   "find . -fprint0 /tmp/x", "find . -fprint out", "find . -newerXY a b",
                   "cat /proc/1/environ", "cat ../.env", "cat ~/.ssh/id_rsa", "grep --file=/etc/passwd x",
                   "diff app /etc/hosts", "ls ../.."):
        assert not command_is_read_only(unsafe, root), unsafe
    Path(root, "escape_link").symlink_to("/etc")
    assert not command_is_read_only("cat escape_link/hosts", root), "symlink escape"
    judged = PermissionPolicy("smart", judge=lambda command: True, workspace_root=root)
    run_tool = ToolRegistry(build_workspace_tools(root)).get("run_command")
    assert judged.decide(run_tool, call("j1", "run_command", command="sort data.txt")).allowed
    assert not judged.decide(run_tool, call("j2", "run_command", command="sort /proc/1/environ")).allowed


def check_repetition_unknown_tool_and_bad_args(root: str) -> None:
    same = call("r", "list_files")
    chat = scripted(*[turn("", [same]) for _ in range(10)])
    result = AgentLoop(chat=chat, tools=ToolRegistry(build_workspace_tools(root)), system_prompt="s",
                       workspace_root=root).run("loop forever")
    assert result.status == "stopped_repetition", result.status
    assert [r.outcome for r in result.tool_calls][:3] == ["ok"] * 3, result.tool_calls
    bad = ToolCall("b1", "write_file", {"__invalid_json__": "{oops"}, "{oops")
    chat = scripted(turn("", [call("u1", "deploy_to_prod"), bad, call("m1", "read_file")]), turn("ok"))
    outcomes = [r.outcome for r in AgentLoop(chat=chat, tools=ToolRegistry(build_workspace_tools(root)),
                                             system_prompt="s", workspace_root=root).run("x").tool_calls]
    assert outcomes == ["unknown_tool", "error", "error"], outcomes


def check_large_output_and_max_turns(root: str) -> None:
    big = Tool("dump", "big output", object_schema({}), lambda args: "x" * 50_000, read_only=True)
    sizes: List[int] = []
    measure = Tool("measure", "size of saved outputs", object_schema({}), read_only=True,
                   handler=lambda args: str(sizes.extend(f.stat().st_size for f in (Path(root) / ".agent_outputs").rglob("*.txt"))))
    chat = scripted(turn("", [call("d1", "dump")]), turn("", [call("m1", "measure")]), turn("summarised"))
    result = AgentLoop(chat=chat, tools=ToolRegistry([big, measure]), system_prompt="s", workspace_root=root).run("dump")
    tool_message = next(m for m in result.messages if m["role"] == "tool")
    assert len(tool_message["content"]) < 5_000 and ".agent_outputs/run-" in tool_message["content"], tool_message
    assert sizes == [50_000], "the full text is readable during the run"
    assert not (Path(root) / ".agent_outputs").exists(), "and removed when the run ends"
    endless = scripted(*[turn("", [call(f"l{i}", "list_files", path=str(i % 2))]) for i in range(5)])
    capped = AgentLoop(chat=endless, tools=ToolRegistry(build_workspace_tools(root)), system_prompt="s",
                       workspace_root=root, config=AgentLoopConfig(max_turns=3)).run("go")
    assert capped.status == "max_turns" and capped.turns == 3, capped.status


def check_compaction() -> None:
    history = [{"role": "system", "content": "sys"}, {"role": "user", "content": "goal"}]
    for i in range(20):
        history.append({"role": "assistant", "content": "", "tool_calls": [
            {"id": f"t{i}", "type": "function", "function": {"name": "read_file", "arguments": "{}"}}]})
        history.append({"role": "tool", "tool_call_id": f"t{i}", "content": "y" * 2_000})
    assert needs_compaction(history, context_limit=10_000)
    compacted = compact_messages(history, lambda prompt: "SUMMARY of earlier work", keep_recent=5)
    assert compacted[0]["content"] == "sys" and compacted[1]["content"] == "goal", compacted[:2]
    assert "SUMMARY of earlier work" in compacted[2]["content"] and compacted[3]["role"] != "tool", compacted[2:4]
    assert not needs_compaction(compacted, context_limit=10_000), len(compacted)
    fallback = compact_messages(history, lambda prompt: (_ for _ in ()).throw(RuntimeError("down")))
    assert "could not be summarised" in fallback[2]["content"], fallback[2]
    chat = scripted(turn("", [call("big", "read_file", path="f")]), turn("done"))
    loop = AgentLoop(chat=chat, tools=ToolRegistry(), system_prompt="s",
                     summarizer=lambda p: "S", config=AgentLoopConfig(context_limit_tokens=2_000))
    assert loop.resume(list(history)).compactions >= 1


def main() -> None:
    with tempfile.TemporaryDirectory() as root:
        check_write_run_and_finish(root)
        check_permissions_and_sandbox(root)
        check_repetition_unknown_tool_and_bad_args(root)
        check_large_output_and_max_turns(root)
    check_compaction()
    print("NAUTILUS LOOP CHECK PASSED")


if __name__ == "__main__":
    main()
