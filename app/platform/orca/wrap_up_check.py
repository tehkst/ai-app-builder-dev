"""Check for the wrap-up turn (found in the real-code pilot: an Audit of a 230-file app used all 60
turns reading files and returned nothing). An employee that runs out of turns without calling
final_output gets a short last chance to hand over what it learned; its usage counts both parts; an
employee that still doesn't answer returns no result, as before; the Audit tells the auditor its budget."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from app.platform.nautilus.messages import ChatTurn, ToolCall
from app.platform.orca.employee_runner import WRAP_UP, WRAP_UP_TURNS, run_employee
from app.platform.orca.workforce import load_workforce

SCHEMA = {"type": "object", "required": ["summary"], "properties": {"summary": {"type": "string"}}}


def _turn(name: str, args: Dict[str, Any], n: int) -> ChatTurn:
    call = ToolCall(f"c{n}", name, args, json.dumps(args))
    message = {"role": "assistant", "content": "", "tool_calls": [
        {"id": call.call_id, "type": "function", "function": {"name": name, "arguments": call.raw_arguments}}]}
    return ChatTurn("", [call], message, "deepseek", "deepseek-v4-pro", {"prompt_tokens": 100, "completion_tokens": 10})


def scripted(answers_after_wrap_up: bool):
    seen: List[str] = []

    def chat(messages, tools):
        n = len(seen)
        seen.append(str(messages[-1].get("content") or ""))
        last_call = next((m for m in reversed(messages) if m.get("role") == "assistant"), {}).get("tool_calls") or []
        if last_call and last_call[0]["function"]["name"] == "final_output":
            return ChatTurn("Done.", [], {"role": "assistant", "content": "Done."}, "deepseek", "deepseek-v4-pro",
                            {"prompt_tokens": 100, "completion_tokens": 10})
        if any(WRAP_UP in str(m.get("content") or "") for m in messages if m.get("role") == "user") and answers_after_wrap_up:
            return _turn("final_output", {"summary": "what I read so far"}, n)
        return _turn("list_files", {"path": "." if n % 2 else ""}, n)  # keeps reading, never finishes
    return chat, seen


def main() -> None:
    employee = load_workforce().for_responsibility("audit_codebase")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "index.js").write_text("console.log(1)\n")
        events: List[str] = []
        chat, seen = scripted(answers_after_wrap_up=True)
        result = run_employee(employee, assignment="audit", workspace_root=str(root), chat=chat, output_schema=SCHEMA,
                              allow_writes=False, allow_execution=False, max_turns=4,
                              usage_sink=(usage := []), on_event=lambda e, p: events.append(e))
        assert result.output == {"summary": "what I read so far"}, (result.output, result.run.status)
        assert len(seen) == 6 and "wrap_up" in events, (len(seen), events)
        assert usage[0]["calls"] == 6 and usage[0]["input"] == 600, "usage counts the turns before and after"

        chat, seen = scripted(answers_after_wrap_up=False)
        result = run_employee(employee, assignment="audit", workspace_root=str(root), chat=chat, output_schema=SCHEMA,
                              allow_writes=False, allow_execution=False, max_turns=4, usage_sink=(usage := []))
        assert result.output is None and result.run.status == "max_turns"
        assert len(seen) == 4 + WRAP_UP_TURNS and usage[0]["calls"] == 4 + WRAP_UP_TURNS, "the last chance is short"

    from app.platform.clients.audit import MAX_TURNS, assignment

    health = {"size": {"lines": 1, "files": 1}, "overall": {"grade": "B"}, "areas": [], "all_risks": []}
    brief = assignment("demo", health)
    assert f"You have {MAX_TURNS} turns" in brief and f"by turn {MAX_TURNS - 5}" in brief, brief[-400:]
    print("WRAP-UP CHECK PASSED")


if __name__ == "__main__":
    main()
