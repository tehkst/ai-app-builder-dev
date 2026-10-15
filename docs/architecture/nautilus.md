# Nautilus: tool-calling agent loop (`app/platform/nautilus/`)

*Why the name:* a nautilus grows its shell in a spiral, one chamber per stage, sealing older
chambers behind it. Nautilus works the same way: each turn of the loop adds to the work, and
older history is sealed off into a summary (compaction) as the session grows.

Until now every model call in the platform was **one prompt in, text (or a JSON contract)
out**. The role agents (`generic_agent.py`) "can only think and respond with text", and the
native coding agent (`app/platform/coding_agent/`) runs a **platform-driven** edit → test →
repair pipeline: the platform decides each step and asks the model for a JSON edit contract.

Nautilus adds a **model-driven tool-calling loop**: the model itself chooses which tool to call
next (read, list, write, run), sees the result and keeps going until the task is done, inside a
generated-app workspace. The two are complementary: `coding_agent` keeps its governed,
evidence-recorded pipeline for platform changes, and a later step could let its repair phase
use Nautilus instead of a single repair prompt.

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
from app.platform.nautilus.service import run_workspace_agent, run_recipe_file

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
- **Live provider verification in CI.** `live_smoke_check.py` exists but no CI workflow runs
  it yet; it must be run with a real key (see Checks).

## Checks

- `loop_check.py`, `recipe_check.py` and `http_check.py` run in `validate_all`
  (local/ci/production profiles) and need no network or API keys. `http_check.py` drives the
  real HTTP code of both adapters against a local fake server that plays the model.
- `live_smoke_check.py` runs against the real provider (a few cents per run) and is in the
  `ai-integration` profile: `AI_PROVIDER=deepseek python -m app.platform.validate_all --profile ai-integration`.
