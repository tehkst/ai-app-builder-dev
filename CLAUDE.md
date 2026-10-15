# CLAUDE.md

Repo-specific instructions for AI coding agent sessions working on AI Software Factory
(`tehkst/ai-app-builder-dev`). This file is read directly by Claude Code (terminal and
claude.ai/code); `AGENTS.md` at the repo root is a symlink to this file so Codex sessions get
the same instructions. Where a convention below differs by tool (e.g. the commit trailer), it's
called out explicitly - everything else applies equally to both.

**Keep this file current.** It is the project's working memory across sessions and tools. When
you finish work that changes the current state, roadmap or a decision below, update the relevant
section in the same PR.

## Mission

AI Software Factory is an **AI company staffed by AI employees**: each employee knows its own
job, an orchestrator runs the show, and the company builds and runs software for customers with
minimal founder involvement. Autonomy widens only through governance (constitution principle 6,
`company/constitution/README.md`): actions move to "no approval needed" by recorded board
resolution, backed by evidence that the gates hold. The full plan (roster, orchestrator, autonomy
tiers, build order) is `company/strategy/ai-workforce-plan.md`; read it before working on agents
or orchestration.

## Current state (update as it changes; last updated 2026-10-15)

- **Execution engine: done.** Nautilus (`app/platform/nautilus/`), a model-driven tool-calling
  agent loop with permissions, recipes, retry-until-checks-pass and context compaction. Merged in
  PR #538. Verified live against DeepSeek in CI on every PR. Guide: `docs/architecture/nautilus.md`.
- **Repair flow: done.** PR #539 connects Nautilus to the generated-app self-healing loop
  (`services/nautilus_repair_service/`): Nautilus proposes a fix on a scratch copy of the
  workflow's sandbox without executing generated code; the existing approval gate and executor
  apply it. Proposals are in-memory (lost on restart). No Mission Control UI yet.
- **Employees: thin.** 16 role agents (`agents/skills/*/skills.md`, ~13 lines each); most
  specialist handlers (`agents/specialists/`) are deterministic code, not model-driven work.
- **Orchestrator: missing.** `agents/orchestrator.py` emits a fixed 5-task plan,
  `builtin.orchestrator_agent` returns static advice, and `pipeline/mission_pipeline.py` is a
  read-only aggregator (its "auto-completed" stages are labels, not work). Nothing yet dispatches
  employees and loops until quality gates pass. **This is the main gap.**

## Roadmap (next steps, in order)

1. ~~Merge PR #539 (Nautilus repair flow).~~ Done.
2. Workforce registry: `company/workforce/` role files adapted from agency-agents (MIT, credit
   them) + manifest (department, tools, permission mode, autonomy tier); loader registers each as
   an `AgentDefinition` with a Nautilus-backed handler.
3. Executing orchestrator (NEXUS-style phases, Dev↔QA loop with max 3 attempts then escalate,
   structured handoffs, durable state) on the existing task queue (`services/agent_task_service`,
   `agents/worker.py`).
4. Wave 1 employees and one end-to-end mission: founder intent → shipped PR, with gates.
5. Autonomy tiers enforced in code; then waves 2 (run the platform) and 3 (grow the business).

## Before grepping the codebase, check the architecture graph

This repo has a real, AST-derived architecture knowledge graph
(`app/platform/architecture_knowledge_graph/`) covering module import dependencies,
authority/governance ownership, ADRs, delivery lineage, and function/class-level call edges. It
already knows the answer to most "is X relevant to Y" / "what depends on this" questions.

**Before manually grepping the codebase to answer that kind of question, run this first:**

```
python -m app.platform.architecture_knowledge_graph.relevance <path/to/file.py>
```

This prints a plain-text report for the given module: what it depends on, what depends on it
(direct imports both ways), its functions/classes, and which functions elsewhere call into it
(only unambiguous matches - an ambiguous call site, same function name defined in multiple
places, is reported as unresolvable rather than guessed). It needs no database and no running
server - pure AST + filesystem - so it works in any checkout, including a fresh session with no
prior context. It takes up to ~20 seconds on this repo's current size (it parses every `.py`
file under `app/`); that's expected, not a hang.

Equivalently, invoke the `/code-relevance-check <file or symbol>` skill, which runs the same
command and interprets the result for you.

The full graph (this CLI's data plus runtime/mission/governance projections that do need the
platform database) is queryable via `app.platform.architecture_knowledge_graph.projection.build_graph()`
and is what backs the founder-facing "Architecture" tab in Mission Control and Jarvis's own
conversational context - see that package's other modules if you need more than module/function
relevance (e.g. governance authority, delivery lineage, or the impact-analysis / blast-radius
report).

## CI gates - run these locally before pushing

These are the same checks `.github/workflows/pr-validation.yml` runs on every PR; run them
locally first so CI isn't your first signal of a break:

```
python -m compileall app
python -m app.platform.validate_all --profile ci
python -m app.platform.api_contract
python -m app.platform.gcp.readiness
python -m app.platform.gcp.check
python -m app.platform.gcp.deploy_check
bash infra/scripts/gate.sh
```

Set `PLATFORM_DATABASE_URL` to an isolated sqlite path (e.g.
`sqlite:////tmp/scratch.db`) for local runs unless you specifically need the real
platform Postgres - most of these gates don't need a live database, and pointing at an
unreachable one will make DB-dependent calls slow or fail rather than crash outright (several
already degrade gracefully; see `architecture_knowledge_graph/authority_projection.py` and
`lineage_projection.py` for the pattern if you add a new one).

Some board_room checks (e.g. `natural_conversation_check`, `operating_console.action_flow_check`)
call a real AI provider and need `OPENAI_API_KEY` (or `DEEPSEEK_API_KEY`) exported to pass -
without it they fail in a way that looks like a regression but isn't.

Local environment: `source ~/venv/bin/activate` (Python 3.12, `pip install -r requirements.txt`).
CI runs the main gates on Python 3.11 and the **coding-agent job on Python 3.9**, so don't use
3.10+ runtime syntax (`match`, `X | Y` outside annotations without `from __future__ import
annotations`).

Live-AI checks: `nautilus.live_smoke_check` (CI step "Nautilus live smoke test", DeepSeek) and
coding-agent "Stage D" call real DeepSeek using the `DEEPSEEK_API_KEY` **GitHub Actions
secret**. Stage D can fail transiently on provider slowness (it clones `main`, so a failure on a
PR that doesn't touch `coding_agent/` is usually not caused by the PR); re-check on the next run
before debugging.

Route checks: FastAPI here nests included routers, so `app.routes` does **not** list the
app-build/platform endpoints. Verify an endpoint with `TestClient` instead: a mounted
admin route answers 401/403/503 without auth, a missing one answers 404.

## Conventions

- Work on a branch named `claude/<descriptive-name>`; open PRs with `gh pr create`, a `## Summary`
  and `## Test plan` in the body, and a co-authorship trailer on commits identifying whichever
  agent actually did the work: `Co-Authored-By: Claude <model name> <noreply@anthropic.com>`
  (e.g. `Claude Opus 5.5`) for Claude Code sessions, `Co-Authored-By: Codex <noreply@openai.com>`
  for Codex sessions.
- Secrets: never commit keys or `.env` files (`.gitignore` blocks them). CI uses GitHub Actions
  secrets; runtime uses the credential vault (`credential_vault.service.resolve_credential`, vault
  first, then env var). Never print or log secret values.
- Borrowed designs: adapting open-source ideas is fine; credit the source and licence in the
  module docstring and docs (e.g. Nautilus ← goose, Apache-2.0; workforce roles ← agency-agents,
  MIT). Give adapted systems our own names.
- New checks go in `validate_all.py` `COMMANDS`; checks needing real API keys go in
  `AI_INTEGRATION_CHECKS` (skipped in `ci`/`local`, run in `ai-integration`).
- Keep files under ~200 lines; this convention is self-enforced and checked
  (`repository_projection.py` flags its own `line_rule: "Split Required"` past 200 LOC). Split an
  over-limit file using the existing `part_1.py`/`part_2.py`/... pattern with an `__init__.py`
  that merges their public names (see `app/platform/services/agent_task_service/`).
- No decorative or fabricated data: if a field has no real evidence, say so explicitly rather than
  inventing a plausible-looking value - this is enforced throughout the codebase (architecture
  graph nodes, agent roster profiles, etc.) and reviewers will flag violations.

## Where things live

- **Founder-facing Mission Control** (the platform operator's own admin UI): `app/platform/ui/`
  (page shells and scripts) + `app/platform/organization_console/`, `board_room/`,
  `operating_console/`, `architecture_knowledge_graph/` (backing services). Served at
  `/mission-control/ui`.
- **Customer-facing SaaS Portal** (an AI Software Factory customer building their own app):
  `app/platform/ui/customer_home.py` (served at `/customer/home`) calling
  `app/api/routes/projects.py`, `app/platform/saas_builder/` (app generation/preparation/
  deployment), and `app/platform/services/customer_app_scope_service.py` /
  `generated_app_preview_service.py` for scope drafting and in-browser preview.
- **Generated customer applications themselves** live under `generated_apps/` locally / the
  platform database in production - not part of this platform's own codebase.
- **Company Brain** (durable company memory: constitution, board resolutions, strategy, ADRs,
  missions, executive profiles): `company/`. Strategy and plans for the AI workforce live in
  `company/strategy/`.
- **AI employees and orchestration:** agent registry `agents/registry.py` (`AgentDefinition`,
  `register_agent`, `choose_agent_for_task`); task queue + worker `services/agent_task_service/`,
  `agents/worker.py`; role skill files `agents/skills/`; org chart `organization/registry.py`;
  related layers `delegation/`, `management/`, `pmo/`, `board_room/` (Jarvis founder conversation),
  `pipeline/mission_pipeline.py` (read-only mission view).
- **Nautilus** (agent loop: tools, permissions, recipes, live checks): `app/platform/nautilus/`.
  Employees should run on it rather than on one-shot prompts.
- **Coding agent** (governed edit → validate → repair pipeline for platform changes, Stage D
  live qualification): `app/platform/coding_agent/`. Platform-driven; distinct from Nautilus.
- **Generated-app repair / self-healing loop:** `services/repair_plan_generator_service.py` →
  `repair_approval_gate_service.py` → `repair_executor_service/` → `repair_rerun_coordinator_service.py`,
  coordinated by `services/self_healing_loop_coordinator_service/`; HTTP in
  `api/app_build/repair_routes.py`.

## Decisions log

Short, dated record of decisions that future sessions must not re-litigate. Add new ones at the
bottom; record the reason.

- 2026-10-15 - **Nautilus** is the name of our agent loop (a nautilus grows chamber by chamber and
  seals old ones: the loop and its compaction). Design adapted from goose, credited.
- 2026-10-15 - Default permission for agents is `approve` with no approver (read-only in
  practice). In `smart` mode a `run_command` is auto-approved only if every path operand is
  confined to the workspace **and** either it is on the deterministic read-only allowlist or,
  when a judge is configured (`PermissionPolicy(judge=...)`, `use_llm_judge=True`), the LLM judge
  classifies it read-only. Everything else goes to the approver. Generated application code
  (running the app, its tests or an interpreter on its files) is never executed before founder
  approval; relaxing this needs a board resolution.
- 2026-10-15 - Nautilus repair proposals resolve the sandbox from the workflow run and require
  it inside `APPROVED_SANDBOX_ROOT_BASE`; no API takes a caller-supplied directory.
- 2026-10-15 - Live AI verification runs in CI with GitHub secrets, never with keys in the repo.
  DeepSeek covered; OpenAI needs an `OPENAI_API_KEY` repo secret first.
- 2026-10-15 - Workforce: onboard 63 of agency-agents' 270 roles in three waves (build, run,
  grow), adapted into our format, not bulk-imported; the orchestrator comes before more roles.
  See `company/strategy/ai-workforce-plan.md`.
