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
- **Orchestrator: first version.** Orca (`app/platform/orca/`, guide `docs/architecture/orca.md`)
  runs missions end to end: architect plans → per-task Builder ↔ QA loop (3 attempts, then
  escalate) → integration gate, with JSON-persisted, resumable state and a founder execution
  decision per mission. CLI: `python -m app.platform.orca`. **First live mission completed** 2026-10-15
  (DeepSeek, demo FastAPI app: `/health` + test, verified by checks and an independent pytest run).
  A live mission runs in CI on every PR ("Orca live mission"). Executed commands are limited to
  test runners and read-only inspection (`orca/execution_policy.py`) but are **not OS-isolated**.
  No API/UI yet; not connected to the agent task queue or Board Room.
- **Employees: 3 real, 16 legacy.** Orca's workforce is `company/workforce/` (architect, builder,
  qa_lead; manifest + role files). The 16 legacy role agents (`agents/skills/`, ~13 lines each,
  mostly deterministic handlers in `agents/specialists/`) are untouched and still used by the
  older pipelines. Legacy `agents/orchestrator.py` and `pipeline/mission_pipeline.py` (read-only
  aggregator) remain.

- **Hosting: none.** The Google Cloud project `ai-software-factory-500910` (Cloud Run, Cloud SQL,
  Secret Manager) was shut down and purged by the founder on 2026-10-15. `platform-deploy.yml`
  and `infra/` still target it, so **don't run deploys**; the `gcp.*` CI gates are static source
  checks and still pass. Choose a new host before any production work.

## Roadmap (next steps, in order)

1. ~~Nautilus repair flow (PR #539).~~ Done.
2. ~~Workforce registry + executing orchestrator, minimum version (Orca).~~ Done.
3. ~~Live-model Orca mission check in CI.~~ Done. Next safety step: run executed tests
   (Orca checks, controlled runtime) in containers for OS-level isolation.
4. Orca API + Mission Control view; route founder intent from the Board Room into Orca missions;
   map Orca's execution decision onto the existing approval-gate services.
5. Grow Wave 1: specialist builders (frontend/backend/database), security reviewer, more NEXUS
   phases (discovery, hardening), "fix production issue" missions via the Nautilus repair flow.
6. One end-to-end mission: founder intent → shipped PR, with gates. Then autonomy tiers enforced
   in code and waves 2 (run the platform) and 3 (grow the business).

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

Model availability: `runtime/provider_router.py` `SUPPORTED_MODELS` lists `gpt-5.5-mini`, but on
2026-10-15 OpenAI returned `model_not_found` for it with our key; `gpt-5.5` works for CI. Verify
a model with a live call before relying on it.

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
- File size: aim for ~300 lines; **500 is the hard limit** (`MAX_MODULE_LINES` in
  `architecture_knowledge_graph/repository_projection.py`, which flags `line_rule: "Split
  Required"`; `ui/ui_module_size_check.py` enforces it for `app/platform/ui/`). Split by
  responsibility into named modules (e.g. `orca/engine.py`, `gates.py`, `handoffs.py`). **Don't
  create new `part_1.py`/`part_2.py` splits**: they cut code at arbitrary lines and glue names
  back together via `__init__.py`. Existing ones (from the old 200-line rule) can be merged back
  or split properly when you next change them.
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
- **Orca** (the orchestrator: missions, Builder ↔ QA loop, escalation, mission store, CLI):
  `app/platform/orca/`; its employees: `company/workforce/` (`manifest.yaml` + `roles/*.md`).
  New AI employees are added there, not in `agents/skills/`.
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
  Both `DEEPSEEK_API_KEY` and `OPENAI_API_KEY` repo secrets exist (rotated 2026-10-15); CI runs
  the Nautilus live test on both and the Orca live mission on DeepSeek.
- 2026-10-15 - Workforce: onboard 63 of agency-agents' 270 roles in three waves (build, run,
  grow), adapted into our format, not bulk-imported; the orchestrator comes before more roles.
  See `company/strategy/ai-workforce-plan.md`.
- 2026-10-15 - File-size limit raised from 200 to **500** lines (target ~300), and no new
  `part_N.py` splits. 200 forced arbitrary splits whose merged namespaces hide bugs (e.g.
  `repair_executor_service` parts each define their own history store); files should be split by
  responsibility instead.
- 2026-10-15 - **Orca** is the orchestrator's name (an orca pod is led by a matriarch who knows
  every member's role). Orca is deterministic code; only employees use the model, so the process
  stays predictable and auditable. An employee's manifest `permission_mode` is a ceiling.
- 2026-10-15 - Orca asks the founder once per mission whether generated code may run (checks,
  builder commands). Declined → Orca still plans/builds/reviews and ends `complete_unverified`.
  A failing acceptance check always overrides a QA PASS.
- 2026-10-15 - AI provider errors **pause** an Orca mission (`paused`, resumable with `run`)
  instead of failing it or using up Dev↔QA attempts; found in the first live run, where a missing
  key escalated a mission in 2 seconds. Founders can `retry` an escalated task.
- 2026-10-15 - Builder and QA briefings list the mission's other tasks, and QA judges **only its
  task**: in the first live mission QA failed T1 for lacking a test planned for T2, causing a
  wasted attempt and a duplicated test.
- 2026-10-15 - Founder execution approval covers running the app's **tests**, not arbitrary
  commands: Orca executes only allowlisted test runners and read-only inspection with
  workspace-confined paths (`orca/execution_policy.py`), every task needs at least one such check,
  and "verified" requires every task covered. OS isolation (containers) is still to come.
- 2026-10-15 - Google Cloud project `ai-software-factory-500910` deleted and purged; nothing is
  hosted. Deploy workflows/infra referencing it are stale until a new host is chosen. An exposed
  DeepSeek key was rotated the same day; keys live only in GitHub Actions secrets for CI.
