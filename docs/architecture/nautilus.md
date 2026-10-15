# Tool-calling agent loop (`app/platform/agent_loop/`)

Until now every agent in the platform was **one-shot**: one prompt in, text out
(`generic_agent.py` tells agents they "can only think and respond with text"). This package
adds a **tool-calling loop** so an agent can inspect a generated-app workspace, change files,
run commands, read the results and keep going until the task is done.

The design is adapted from [goose](https://github.com/aaif-goose/goose) (Apache-2.0); the
Rust source file each idea comes from is noted below.

## What's in the package

| Module | What it does | goose origin |
|---|---|---|
| `loop.py` | The reply loop: call the model, run requested tools, feed results back, stop when the model answers without a tool call or `max_turns` is hit. | `agents/agent.rs` |
| `chat_providers.py` | Native function calling for both configured providers: OpenAI Responses (`function_call` items, reasoning items replayed) and DeepSeek chat completions (`tool_calls`, `reasoning_content` preserved). Same credentials and timeouts as `runtime/`. | `crates/goose-providers` |
| `workspace_tools.py` | `read_file`, `list_files`, `write_file`, `run_command`. All paths go through `guards/filesystem_write_guard.py`; commands run without a shell, inside the workspace, with secret-looking env vars removed. | `goose-mcp` developer tools |
| `permissions.py` | Read-only tools always run. Modes: `auto`, `smart` (read-only commands auto-approved by allowlist, optional LLM judge), `approve`, `read_only`. **With no approver, gated calls are denied.** | `permission/permission_judge.rs` |
| `guards.py` | Repetition monitor (the same call 3x in a row is blocked; 3 blocked attempts stop the run) and large-output offloading (>40k chars saved to `.agent_outputs/`, preview returned). | `tool_monitor.rs`, `large_response_handler.rs` |
| `compaction.py` | At 80% of the context limit, the middle of the history is summarised; system prompt, goal and recent messages are kept, and tool-call/result pairs are never split. | `context_mgmt/mod.rs` |
| `recipe.py`, `recipe_runner.py` | Reusable YAML/JSON tasks with parameters, a structured `final_output` (JSON schema), and **retry until success checks pass**. Failed check output is fed back to the agent. | `recipe/`, `agents/retry.rs`, `final_output_tool.rs` |
| `service.py` | `run_workspace_agent(...)` and `run_recipe_file(...)` wired to the configured provider. | - |

## Using it

```python
from app.platform.agent_loop.service import run_workspace_agent, run_recipe_file

result = run_workspace_agent(
    "Add a /health endpoint and make the tests pass",
    workspace_root="generated_apps/acme",
    permission_mode="smart",
    approver=lambda call: founder_approves(call),  # omit -> writes/commands are denied
)
print(result.status, result.final_text)

recipe_result = run_recipe_file("path/to/add_health_endpoint.yaml",
                                workspace_root="generated_apps/acme",
                                parameters={"app_name": "acme"})
```

See the docstring in `recipe.py` for the full recipe format.

## Safety boundaries

- Agents only ever touch their own workspace (`FACTORY_CODE_IMMUTABILITY_RULE`); the
  platform source is never a valid target.
- Default permission mode is `approve` with no approver, i.e. read-only in practice. Write
  access is an explicit decision by the caller.
- `run_command` has no shell, so pipes, redirects and `&&` are unavailable by design.
  It is **not** an OS sandbox: an approved command runs with the platform process's user
  rights. Use `auto` mode only inside the controlled sandbox runtime.

## Not done yet

- **Wiring into existing agents.** Nothing calls the loop yet; `generic_agent.py` and the
  builder/test specialists are unchanged. The natural first adopter is the repair flow
  (`repair_executor`, self-healing loop).
- **MCP extensions** (goose's `extension_manager.rs`). That needs an MCP client dependency.
  `ToolRegistry` is the integration point.
- **Founder approval UI.** `approver` is a plain callback; it is not yet connected to
  Mission Control's approval gates.
- **Live provider verification.** The checks use a scripted model. The OpenAI and DeepSeek
  wire formats are verified against fixtures, not live calls.

## Checks

`agent_loop_check.py` and `recipe_check.py` run in `validate_all` (local/ci/production
profiles). They need no network or API keys.
