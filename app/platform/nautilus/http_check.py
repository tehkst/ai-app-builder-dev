"""Exercises the real HTTP code path of both provider adapters against a local fake server
that plays the model (no network, no API keys). Verifies request headers and payload shape,
and that a tool result makes the round trip back to the provider on the next turn."""
from __future__ import annotations

import json
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock

from app.platform.nautilus import chat_providers
from app.platform.nautilus.loop import AgentLoop
from app.platform.nautilus.permissions import PermissionPolicy
from app.platform.nautilus.tools import ToolRegistry
from app.platform.nautilus.workspace_tools import build_workspace_tools

FAKE_KEY = "test-key-not-real"
WRITE_ARGS = json.dumps({"path": "out.txt", "content": "from fake model"})

OPENAI_REPLIES = [
    {"output": [{"type": "function_call", "id": "fc_1", "call_id": "call_1", "name": "write_file",
                 "arguments": WRITE_ARGS}]},
    {"output": [{"type": "message", "role": "assistant",
                 "content": [{"type": "output_text", "text": "Wrote out.txt"}]}]},
]
DEEPSEEK_REPLIES = [
    {"choices": [{"message": {"role": "assistant", "content": "", "tool_calls": [
        {"id": "call_1", "type": "function", "function": {"name": "write_file", "arguments": WRITE_ARGS}}]}}]},
    {"choices": [{"message": {"role": "assistant", "content": "Wrote out.txt"}}]},
]


def serve(replies: List[Dict[str, Any]]):
    received: List[Dict[str, Any]] = []
    queue = list(replies)

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            received.append({"auth": self.headers.get("Authorization"), "path": self.path, "body": body})
            payload = json.dumps(queue.pop(0)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args: Any) -> None:
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, received


def run_against(server, chat_fn) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory() as root:
        loop = AgentLoop(chat=chat_fn, tools=ToolRegistry(build_workspace_tools(root)), system_prompt="sys",
                         permissions=PermissionPolicy("auto"), workspace_root=root)
        result = loop.run("write out.txt")
        content = (Path(root) / "out.txt").read_text()
    server.shutdown()
    return {"result": result, "content": content}


def check_openai() -> None:
    server, received = serve(OPENAI_REPLIES)
    url = f"http://127.0.0.1:{server.server_port}/v1/responses"
    with mock.patch.object(chat_providers, "OPENAI_API_URL", url), \
            mock.patch.object(chat_providers, "_openai_api_key", lambda: FAKE_KEY):
        outcome = run_against(server, chat_providers.openai_chat("gpt-5.5"))
    assert outcome["result"].status == "completed" and outcome["content"] == "from fake model", outcome
    assert [r["auth"] for r in received] == [f"Bearer {FAKE_KEY}"] * 2, received
    first, second = received[0]["body"], received[1]["body"]
    assert first["model"] == "gpt-5.5" and {t["name"] for t in first["tools"]} >= {"write_file", "read_file"}, first
    assert all(t["type"] == "function" for t in first["tools"]), first["tools"]
    kinds = [item.get("type") or item.get("role") for item in second["input"]]
    assert kinds == ["system", "user", "function_call", "function_call_output"], kinds
    assert second["input"][-1]["call_id"] == "call_1" and "Wrote" in second["input"][-1]["output"], second


def check_deepseek() -> None:
    server, received = serve(DEEPSEEK_REPLIES)
    url = f"http://127.0.0.1:{server.server_port}/chat/completions"
    with mock.patch.object(chat_providers, "DEEPSEEK_API_URL", url), \
            mock.patch.object(chat_providers, "_deepseek_api_key", lambda: FAKE_KEY):
        outcome = run_against(server, chat_providers.deepseek_chat("deepseek-v4-pro"))
    assert outcome["result"].status == "completed" and outcome["content"] == "from fake model", outcome
    assert [r["auth"] for r in received] == [f"Bearer {FAKE_KEY}"] * 2, received
    first, second = received[0]["body"], received[1]["body"]
    assert first["stream"] is False and first["tools"][0]["type"] == "function", first
    assert "name" in first["tools"][0]["function"], first["tools"][0]
    roles = [m["role"] for m in second["messages"]]
    assert roles == ["system", "user", "assistant", "tool"], roles
    assert second["messages"][2]["tool_calls"][0]["id"] == "call_1", second["messages"][2]
    assert second["messages"][3]["tool_call_id"] == "call_1", second["messages"][3]
    assert not any(key.startswith("_") for m in second["messages"] for key in m), second["messages"]


def check_missing_key() -> None:
    with mock.patch.object(chat_providers, "_deepseek_api_key", lambda: None):
        result = AgentLoop(chat=chat_providers.deepseek_chat("deepseek-v4-pro"), tools=ToolRegistry(),
                           system_prompt="s").run("x")
    assert result.status == "provider_error" and "DEEPSEEK_API_KEY" in (result.error or ""), result


def main() -> None:
    check_openai()
    check_deepseek()
    check_missing_key()
    print("NAUTILUS HTTP CHECK PASSED")


if __name__ == "__main__":
    main()
