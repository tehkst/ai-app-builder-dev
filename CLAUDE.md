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
  apply it. Proposals are in-memory (lost on restart). No Mission Control UI yet. Served by the
  production server as founder-only POSTs `/mission-control/repair/{overview,propose,approve,
  reject,apply,rerun}` (`app/platform/repair_console/service.py`, body `{token, workflow_run_id}`)
  since clean-up batch 4; the old `/platform/app-build/*` routes and `app/main.py` are gone.
- **Orchestrator: first version.** Orca (`app/platform/orca/`, guide `docs/architecture/orca.md`)
  runs missions end to end: architect plans → per-task Builder ↔ QA loop (3 attempts, then
  escalate) → integration gate, with JSON-persisted, resumable state and a founder execution
  decision per mission. CLI: `python -m app.platform.orca`. **First live mission completed** 2026-10-15
  (DeepSeek, demo FastAPI app: `/health` + test, verified by checks and an independent pytest run).
  A live mission runs in CI on every PR ("Orca live mission"). Executed commands are limited to
  test runners and read-only inspection (`orca/execution_policy.py`) but are **not OS-isolated**.
  Founders follow and decide on missions in **Mission Control → Home** (API `/mission-control/orca/*`
  in `server.py`, background runs in `orca/runner.py`; the classic page keeps an Orca Missions view,
  `ui/orca_missions_script.py`). **Jarvis hand-off:** a proposal that names an app workspace (e.g.
  "in the demo app, ...") offers "Build it in 'demo' with the AI team (Orca)"; the founder confirms,
  then it starts (classic page: opens Orca Missions pre-filled). Platform proposals never get this button. Not yet connected
  to the agent task queue.
- **Mission Control v2: done (5 of 5)**, the default at `/mission-control/ui` (alias `/mission-control/v2`;
  `app/platform/ui/mc2/`, check `mc2_check`). Redesign approved 2026-10-16 (prototype v3): the founder's view only (customers get
  the separate Customer Portal). Menu Home · Customers · Company · Settings; Jarvis is a side panel
  on every screen and the only place to type; Home merges "Needs you" (decisions, stopped/escalated/
  paused missions, publish requests, a blocked platform mission) with "All work" (Orca + platform
  missions, details with each employee's trail). Orca has no page of its own. **Customers** shows
  business numbers, publish decisions (approve / send back / open the PR with the typed phrase; no
  deploy until there is a host) and every customer with their apps (`customers_overview/service.py`,
  POST `/mission-control/customers/list`; scoped apps collapsed per amended chain plus one-shot
  SaaS-builder apps; "building" only while the workflow runs). **Company** explains how work gets
  done, lists the AI team and the planned hires (manifest `planned_hires`, via `orca/workforce`) and
  links to classic Insights (organisation, memory, architecture, delivery history). **Settings** groups
  the classic controls into AI, Email, GitHub (health, imported repos), Credentials (reveal asks
  first, hides after 30s), Deployment (paused: no host) and Log out. Sign-in is built in (`mc2/login.py`).
  The previous page lives at **`/mission-control/classic`** (banner pointing back). v2 links there for
  Insights and Mission Execution; the Jarvis panel opens classic for the steps it can't run yet:
  Board Room actions (`#board`: workflow actions, founder decision flow, UI/UX deploy) and governed
  execution (`#executions`: GitHub PR/merge/verification/rollback approval panels). Classic
  Executions, Workflows and Projects look like placeholders in the markup but scripts mount live
  panels into them, so don't remove them. Retire classic once those flows move over.
- **Employees: 5 real, 16 legacy.** Orca's workforce is `company/workforce/` (architect, builder,
  frontend_developer, qa_lead, ux_designer; manifest + role files). Frontend tasks route to the
  Frontend Developer and need the UX Designer's PASS after QA. The 16 legacy role agents (`agents/skills/`, ~13 lines each,
  mostly deterministic handlers in `agents/specialists/`) are untouched and still used by the
  older pipelines. Legacy `agents/orchestrator.py` and `pipeline/mission_pipeline.py` (read-only
  aggregator) remain.

- **Hosting: none.** The Google Cloud project `ai-software-factory-500910` (Cloud Run, Cloud SQL,
  Secret Manager) was shut down and purged by the founder on 2026-10-15. `platform-deploy.yml`
  and `infra/` still target it, so **don't run deploys**; the `gcp.*` CI gates are static source
  checks and still pass. Choose a new host before any production work.
- **Known production issue (unfixed): UI/UX preview requests return 503.** `ui_ux_agent.propose_ui_change`
  (`app/platform/ui_ux_agent/service.py`) makes an LLM call **and** a full headless-Chromium
  (Playwright) render synchronously inside one HTTP request. On the old Cloud Run service (512Mi
  memory, 1 CPU) a live request returned 503. Raising the request timeout to 600s (#528) did not
  help and was reverted (#529, production rolled back to `ai-software-factory-production-00236-g9k`).
  Likely cause, **unconfirmed**: memory, not time. When choosing the new host: give the service more
  memory, or move the render out of the request (background job/worker, poll for the result), and
  confirm with a live test before calling it fixed.

## Roadmap (next steps, in order)

1. ~~Nautilus repair flow (PR #539).~~ Done.
2. ~~Workforce registry + executing orchestrator, minimum version (Orca).~~ Done.
3. ~~Live-model Orca mission check in CI.~~ Done. Next safety step: run executed tests
   (Orca checks, controlled runtime) in containers for OS-level isolation.
4. ~~Orca API + Mission Control view; Board Room hand-off.~~ Done. Next: map Orca's execution
   decision onto the approval-gate services; move missions into the platform DB; let Jarvis report
   Orca mission progress back in the conversation.
5. Grow Wave 1: specialist builders (frontend/backend/database), security reviewer, more NEXUS
   phases (discovery, hardening), "fix production issue" missions via the Nautilus repair flow.
6. One end-to-end mission: founder intent → shipped PR, with gates. Then autonomy tiers enforced
   in code and waves 2 (run the platform) and 3 (grow the business).
7. ~~Mission Control v2 stages 1-5~~ (done 2026-10-16). Next: move the remaining classic-only Board Room
   steps and the execution approval panels into v2, then retire `/mission-control/classic`;
   5 make v2 the default, then retire the classic placeholders and duplicate chats.
8. ~~Decide on `/platform/app-build/*`~~: done 2026-10-16 - the repair flow moved to
   `/mission-control/repair/*` and `app/main.py` was retired (clean-up batch 4).
9. **Housecleaning** (audit 2026-10-16: ~60k of ~114k lines reachable from production; ~27k only from
   `app/main.py`; 219 checks (~18k lines) not in `validate_all`; ~107 unreachable modules). Batches, one
   PR each, all gates green: 1 deploy leftovers + root clutter; 2 unregistered checks (register or
   delete); 3 unreachable modules (verify CLI entry points against CI/scripts/docs first); 4 retire
   `app/main.py`; 5 architecture map of every remaining area (replaces the stale
   `docs/DEPENDENCY_MAP.md`). Live legacy that overlaps Orca (old platform-mission pipeline,
   legacy role agents, pmo, delegation) is migrated, not deleted.
   Progress: batch 1 (#552), 2a (#553, +61 checks), 2b (#554), 3 (#555, 127 files) done; batch 4
   retires `app/main.py` (100 files). Code that registered checks still exercise stays even if only the
   old app builder used it; retire it with those checks when that pipeline moves onto Orca.
   Lessons: some code is referenced by **file path** (checks reading source files, capability
   evidence paths in `capability_intelligence/service.py`, `saas_builder/check.py` importing the
   reference app by path, `digital_twin` using `coding_agent/qualification/harness.py`); grep paths
   as well as module names before deleting. Pre-existing: four capability evidence paths point at
   files that became packages (`services/{workflow_run_persistence,agent_execution_planner,
   agent_execution_bridge,agent_workflow_executor}_service.py`).
10. **Orchestration upgrades (after clean-up)**: keep our own engine (Orca + Nautilus) and borrow
   LangGraph's ideas: dependency-aware parallel tasks, every step saved to the DB, live progress
   events (then replay). LangGraph/LangChain/LangSmith were removed from requirements in batch 4
   (nothing imported them); PyYAML is now listed explicitly (it used to arrive via LangChain).

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

One app: **production runs `app.platform.server:app`** (see `scripts/start.sh`; Mission Control
and `/mission-control/*` live there, POST bodies carry the founder token checked by
`auth.service.require_founder`). The old second app `app/main.py` was retired in clean-up batch 4.

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
  `/mission-control/ui` (redesign, `ui/mc2/`); the previous page at `/mission-control/classic`.
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
- 2026-10-15 - Frontend Developer and UX Designer joined the workforce. Tasks carry a `specialty`;
  frontend tasks need QA **and** UX PASS. Employees improve the apps Orca builds, not Mission Control
  itself; platform UX is improved by coding sessions (e.g. the plain-language Orca page guide).
- 2026-10-15 - Reverted the Cloud Run `--timeout=600` (#529): it didn't fix the UI/UX preview 503s.
  Don't raise timeouts again for that symptom; treat it as a memory/architecture problem (see the
  known production issue above).
- 2026-10-15 - Board Room → Orca is a **pre-fill, not an auto-start**, and only for proposals that
  name exactly one app workspace and don't mention the platform: Board Room missions are platform
  missions by default and Orca can't change the platform, so a platform goal must never be handed
  to Orca against a customer app. The founder still presses Start. The Board Room
  proposal id is stored only as a traceability label (`started_from_board_room`).
- 2026-10-16 - Mission Control v2: the Jarvis panel's Orca hand-off asks the founder with a
  confirm dialog, then starts the mission (there is no Orca page to pre-fill any more). Same gating
  as before: only offered for proposals naming exactly one app workspace, never platform goals.
- 2026-10-16 - Orchestration: build and own our engine (Orca + Nautilus), borrowing LangGraph's
  ideas rather than adopting it. No additional paid AI providers for now (founder's budget); Qwen and
  OpenRouter only offer trials/heavily rate-limited free use. Per-role models (a different model for
  reviewers than builders) is the preferred "debate" when a second provider is affordable.
- 2026-10-16 - Railway is gone for good (constitution already excluded it): `railway.json`, its
  deployment-pack docs and their unregistered checks were removed in clean-up batch 1.
- 2026-10-16 - Runtime settings saves (`/mission-control/runtime/{ai-provider,smtp-provider,
  independent-review}` POST) now require a founder session; they were open to anyone who could reach
  the server. Reads stay public (no secrets). The classic page sends its token for these saves.
- 2026-10-16 - Clean-up 2b: Jarvis treated "I want AI Software Factory to ... create a mission" as
  product discovery since 0db06280 (Jul 24): the company name contains "software". Fixed in
  `board_room/conversation_mode._product_discovery`. Stale checks updated (afos_008 Agents ->
  Organisation, Jarvis image attachments since #530, Pub/Sub UNKNOWN since Terraform was deleted)
  and registered. `customer_home.py` (1,057 lines) is exempt from the UI size check until it is split.
- 2026-10-15 - Google Cloud project `ai-software-factory-500910` deleted and purged; nothing is
  hosted. Deploy workflows/infra referencing it are stale until a new host is chosen. An exposed
  DeepSeek key was rotated the same day; keys live only in GitHub Actions secrets for CI.
