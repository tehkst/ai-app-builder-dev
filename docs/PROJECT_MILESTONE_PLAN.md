# AI Software Factory — Project Milestone Plan

# Current Handover Snapshot

Repository: `tehkst/ai-app-builder-dev`

Current merged baseline after hosted Railway browser MVP validation: `1e533de Fix dashboard rendered JavaScript syntax`

Current completed milestone: V87 — End-to-End MVP Launch Smoke, plus hosted Railway browser MVP operational validation.

Current active next milestone: V88 — Real DB-Preview File Generation From Browser App Build.

Current project status: Hosted private MVP browser shell is operational on Railway. The next product gap is generating actual DB-preview application files from the browser app-build flow while preserving all safety boundaries.

Primary product direction:

Build the minimum self-building and self-healing app factory loop:

Generate app/module files -> store generated files as DB-preview records -> review/edit generated files in browser -> approval-gated static preview/materialization -> run approved app in sandbox -> capture logs/errors -> analyze failure -> propose repair -> approve repair -> apply repair -> re-run -> roll out passing module.

Near-term checkpoints:

- V70 — first controlled sandbox app run. Complete.
- V71 — runtime log capture. Complete.
- V72 — runtime failure analysis. Complete.
- V73 — repair plan generation. Complete.
- V74 — repair approval gate. Complete.
- V75 — repair executor. Complete.
- V76 — re-run after repair. Complete.
- V77 — first complete self-healing loop. Complete.
- V78 — self-build module request flow. Complete.
- V79 — module rollout gate. Complete.
- V80 — internal dogfooding milestone. Complete.
- V81 — production config and healthcheck. Complete.
- V82 — persistent state store. Complete.
- V83 — auth and admin access gate. Complete.
- V84 — background job runner. Complete.
- V85 — hosted sandbox boundary. Complete.
- V86 — Railway/Gcore deployment pack. Complete.
- V87 — end-to-end MVP launch smoke. Complete.
- Hosted Railway browser MVP validation. Complete.
- V88 — real DB-preview file generation from browser app build. Active next milestone.

Current safety boundary:

Controlled runtime execution, runtime log capture, classification-only runtime failure analysis, plan-only repair plan generation, approval-only repair gating, approval-gated sandbox repair execution, re-run-after-repair coordination, first self-healing loop coordination, request-tracking-only self-build module requests, gate-only module rollout approval/rejection, demonstration-only internal dogfooding module flow, readiness-only production config/healthcheck inspection, persistent state inspection, admin access gating, background job readiness inspection, hosted sandbox boundary checking, deployment-pack file/config validation, final end-to-end MVP launch-readiness smoke aggregation, hosted Railway browser dashboard loading, browser admin login, and browser app-build workflow orchestration are implemented. The safety boundary remains DB-preview-only for generated files unless a later approval-gated milestone explicitly enables preview/materialization. No generated code should execute and no generated files should be written to disk during V88.

---

This file is the source of truth for the current development roadmap.

## Planning Rule

Do not insert, rename, reorder, or replace milestones without explicit user confirmation.

The user has explicitly approved the post-V87 roadmap V88-V94. V88 is the active next milestone. Work one milestone at a time. Do not skip ahead to V89 or later without first completing and merging V88, unless the user explicitly changes the plan.

## Project Working Rule

Use the direct GitHub connection for every step the assistant can safely handle, including repository inspection, branch creation, file creation, file updates, commits, PR creation, PR updates, PR review/status inspection, and PR merging.

Only involve the local Mac workflow when direct GitHub access cannot perform the step or when local validation is required. The user's local role should normally be limited to `git pull` / branch sync, running validation commands, pasting terminal output, and resolving local environment issues.

Do not ask for VS Code/manual file editing unless the user explicitly requests it. Prefer GitHub-side commits and PRs first, then local sync/test.

When roadmap or handover updates are requested, the assistant should update `docs/PROJECT_MILESTONE_PLAN.md` directly, not only draft instructions for the user.

---

## Current Completed Milestone

### V87 — End-to-End MVP Launch Smoke

Status: Completed and merged via PR #116.

V87 added the final end-to-end MVP launch smoke aggregator and launch-readiness report. It aggregates V81 production config and healthcheck readiness, V84 background job runner readiness, V85 hosted sandbox boundary contract, and V86 Railway/Gcore deployment pack completeness. The final local smoke returned `passed=True` and `launch_readiness_status=ready_for_private_mvp_deployment_setup` while preserving no-deployment, no-runtime, no-generated-execution, no-secret-write, no-public-URL, no-approval-bypass, no-repair, no-restore, and no-rollout safety flags.

### Hosted Railway Browser MVP Validation

Status: Completed after V87 through Railway deployment and follow-up fixes.

Verified hosted baseline:

- Railway deployment is active.
- `/health` returns ready status.
- Platform admin login page works.
- Browser dashboard loads from Railway.
- Rendered dashboard JavaScript passes syntax validation.
- Dashboard buttons can call Railway APIs after browser login.
- `Load Recent Runs` works.
- `Start App Build Session` works.
- Workflow run persistence works.
- Summary/results review loads.
- Safety mode remains DB-preview-only.
- Disk writes remain disabled.
- Generated code execution remains disabled.

Important hosted/browser follow-up PRs and commits:

- PR #123 — Add platform browser admin login.
- PR #124 — Allow browser dashboard shell to load after login.
- PR #125 — Use browser admin JWT for dashboard API calls.
- PR #126 — Fix dashboard JavaScript newline escaping.
- PR #127 — Fix dashboard app request newline escaping.
- Direct main commit `1e533de` — Fix dashboard rendered JavaScript syntax.

Latest verified hosted browser run:

- Workflow run ID: `workflow_run_bac9b0882b6e430589d1c4daac0a89e6`
- Status: `completed`
- Steps: `4/4`
- Generated file count: `0`
- Write mode: `DB preview only`
- Disk writes: `false`
- Generated code execution: `false`

## Active Next Milestone

### V88 — Real DB-Preview File Generation From Browser App Build

Status: Approved as the next active milestone.

Goal:

When a browser app-build session runs, it should create actual generated file records in the database, such as `index.html`, `styles.css`, `app.js`, and `README.md`.

Expected output:

- Browser `Start App Build Session` creates generated file records.
- Generated files are stored as DB-preview records only.
- `Generated Files` panel shows file count greater than 0.
- `Workspace Explorer` lists generated files.
- File preview loads generated content.
- No generated file is written to disk.
- No generated code is executed.

Safety requirements:

- `write_mode = db_preview_only`
- `disk_write_performed = false`
- `filesystem_write_performed = false`
- `generated_code_execution_performed = false`
- No external deployment.
- No approval bypass.
- No generated files written to disk.
- No generated code execution.

Suggested first inspection targets for V88:

- `docs/PROJECT_MILESTONE_PLAN.md`
- `app/platform/api/app_build_routes.py`
- `app/platform/agents/app_build_request_run_check.py`
- `app/platform/services/agent_workflow_executor_service.py`
- `app/platform/services/generated_file_persistence_service.py`
- `app/platform/services/generated_file_version_service.py`
- `app/platform/persistence/models.py`
- Existing generated-file and workspace explorer checks in `app/platform/agents/`

---

## Completed MVP Launch Roadmap

| Milestone | Name | Purpose | Status | PR |
|---|---|---|---:|---:|
| V81 | Production Config & Healthcheck | Add deployment-safe settings, health endpoint, startup validation, provider env docs | Complete | #109 |
| V82 | Persistent State Store | Replace in-memory approval/request/rollout state with database-backed persistence | Complete | #110 |
| V83 | Auth & Admin Access Gate | Add minimum admin login/API gate suitable for hosted MVP | Complete | #111 |
| V84 | Background Job Runner | Move long-running build/run/repair operations into tracked jobs instead of request-bound actions | Complete | #112 |
| V85 | Hosted Sandbox Boundary | Define provider-safe sandbox paths, resource limits, cleanup, and no-production-write guard | Complete | #114 |
| V86 | Deployment Pack for Railway/Gcore | Add Dockerfile/provider config, env template, deploy guide, smoke checks | Complete | #115 |
| V87 | End-to-End MVP Launch Smoke | Validate final private MVP launch-readiness by aggregating completed readiness checks | Complete | #116 |

Provider decision:

- Railway first for fastest MVP deployment, simpler GitHub-based deploys, PostgreSQL add-on, environment variable management, and quick rollback.
- Gcore later if the app needs more controlled infrastructure, regional/security choices, or heavier sandbox isolation.

Launch target after V87:

- Private MVP / closed beta deployment setup, not broad public SaaS.
- Admin-only access acceptable for the first launch.
- Billing, marketplace, multi-tenant team features, and advanced external deployment connectors remain out of scope until after the private MVP setup is explicitly approved.

---

## Handover Update After Hosted Browser MVP Validation

Current merged baseline:

```text
1e533de Fix dashboard rendered JavaScript syntax
```

Completed browser/runtime milestones after the original roadmap:

| Milestone | Name | Status | PR |
|---|---|---:|---:|
| V47 | Filesystem Write Guard / Path Guard | Complete | #56 |
| V48 | Browser Restore Control Panel | Complete | #57 |
| V49 | Browser Workspace File Editor | Complete | #58 |
| V50 | Browser App Builder Workspace | Complete | #59 |
| V51 | Browser Preview / Run Panel | Complete | #60 |
| V52 | Browser Self-Healing Console | Complete | #61 |
| V53 | Browser One-Click Repair Flow | Complete | #62 |
| V54 | Browser App Build Session Launcher | Complete | #64 |
| V55 | Browser App Spec Form / Prompt Builder | Complete | #66 |
| V56 | Browser App Build Results Review Panel | Complete | #68 |
| V57 | Safe Static Preview Renderer | Complete | #70 |
| V58 | Approval-Gated Workspace Materialization Plan | Complete | #72 |
| V59 | Materialization Approval Workflow | Complete | #74 |
| V60 | Materialization Approval History | Complete | #76 |
| V61 | Persistent Approval Record | Complete | #79 |
| V62 | Materialization Execution Gate | Complete | #80 |
| V63 | Safe Workspace Materialization Dry Run | Complete | #82 |
| V64 | Local Sandbox Workspace Writer | Complete | #84 |
| V65 | Manual Browser Test Harness | Complete | #86 |
| V66 | Browser Manual Test Harness Panel | Complete | #88 |
| V67 | Runtime Readiness Detector | Complete | #92 |
| V68 | Runtime Run Plan Builder | Complete | #93 |
| V69 | Runtime Approval Gate | Complete | #94 |
| V70 | First Controlled Sandbox App Run | Complete | #95 |
| V71 | Runtime Log Capture | Complete | #96 |
| V72 | AI Runtime Failure Analyzer | Complete | #99 |
| V73 | Repair Plan Generator | Complete | #100 |
| V74 | Repair Approval Gate | Complete | #101 |
| V75 | Approval-Gated Repair Executor | Complete | #102 |
| V76 | Re-run After Repair | Complete | #103 |
| V77 | First Self-Healing Loop | Complete | #104 |
| V78 | Self-Build Module Request Flow | Complete | #105 |
| V79 | Module Rollout Gate | Complete | #106 |
| V80 | Internal Dogfooding Milestone | Complete | #107 |
| V81 | Production Config & Healthcheck | Complete | #109 |
| V82 | Persistent State Store | Complete | #110 |
| V83 | Auth & Admin Access Gate | Complete | #111 |
| V84 | Background Job Runner | Complete | #112 |
| V85 | Hosted Sandbox Boundary | Complete | #114 |
| V86 | Railway/Gcore Deployment Pack | Complete | #115 |
| V87 | End-to-End MVP Launch Smoke | Complete | #116 |

Current product capability:

The hosted system can serve the private admin browser dashboard on Railway, authenticate an admin browser session, call protected dashboard APIs, list recent workflow runs, launch a browser app-build workflow, persist workflow metadata, and review workflow summaries. The older local/sandbox product capability also includes generated-file planning, runtime readiness detection, runtime run planning, approval-gated sandbox operations, runtime log capture, runtime failure classification, repair planning, repair approval, repair execution, rerun coordination, self-healing loop coordination, self-build request tracking, module rollout gating, hosted sandbox boundary checks, and deployment pack readiness.

Current product gap:

The hosted browser workflow completes app-build orchestration but currently produces `generated_file_count = 0`. V88 must connect the browser app-build workflow to real DB-preview generated file persistence while keeping disk writes and generated-code execution disabled.

---

## Post-V87 Roadmap — Hosted Browser MVP Productization

### V88 — Real DB-Preview File Generation From Browser App Build

Goal: Start App Build Session creates actual DB-preview generated file records.

Success criteria:

- Start App Build Session creates generated file records.
- Generated files remain DB-preview-only.
- `disk_write_performed = false`.
- `generated_code_execution_performed = false`.
- Generated Files / Workspace Explorer shows files.
- File preview loads content.
- No filesystem writes.

### V89 — Browser Generated File Review & Edit Flow

Goal: Allow reviewing and editing DB-preview generated files from the browser dashboard.

Success criteria:

- Select generated file from Workspace Explorer.
- View file content.
- Edit preview content.
- Save edited DB-preview content.
- Version record created.
- No disk write.
- No generated code execution.

### V90 — Approval-Gated Static Preview Materialization

Goal: Prepare a safe approval-gated flow that can materialize selected DB-preview files into a static preview sandbox only after explicit approval.

Success criteria:

- Preview plan generated first.
- Risk/safety summary shown.
- Approval required before materialization.
- Only static files allowed.
- No backend/server code execution.
- No external deployment.

### V91 — Static Preview Browser Smoke Test

Goal: Render approved static preview and verify it can be opened safely in the browser.

Success criteria:

- Approved static preview opens in isolated route/session.
- HTML/CSS/JS static app displays.
- Browser logs/errors captured.
- No server-side generated code execution.
- Preview can be stopped/cleared.

### V92 — Self-Healing Repair Proposal for Generated Preview Files

Goal: When preview/browser smoke test fails, system should analyze logs and propose DB-preview file repairs.

Success criteria:

- Browser/preview error captured.
- Repair proposal generated.
- Repair shown as diff.
- Approval required before applying repair.
- Repair updates DB-preview files only.

### V93 — Approval-Gated Repair Apply & Re-Test Loop

Goal: Complete safe repair loop: approve repair, update DB-preview files, re-preview, re-test.

Success criteria:

- Approved repair applied to DB-preview records.
- Version history records before/after.
- Static preview rerun.
- Browser smoke result updates.
- No approval bypass.

### V94 — Private MVP Demo Script & Operator Checklist

Goal: Create a repeatable demo/test script for private MVP users/operators.

Success criteria:

- One browser-based demo flow documented.
- Admin login steps documented.
- Known limitations listed.
- Safety boundaries listed.
- Troubleshooting checklist included.

---

## Tentative Post-V94 Direction — Self-Building SaaS Module Rollout

Status: Tentative roadmap guidance only. Not active implementation scope.

These milestones are directional and are not approved for active implementation. They exist to keep the project aligned toward a production-grade self-building and self-healing SaaS platform. Active work remains focused on V88-V94 unless the user explicitly activates a later milestone.

### V95 — SaaS Module Blueprint Generator (Tentative)

Goal: Generate real SaaS module blueprints, contracts, file structures, and dependency plans for platform features before implementation.

Success direction:

- Generate module blueprint and product objective.
- Define expected UI routes, API boundaries, data contracts, and file structure.
- Identify dependencies and safety boundaries before code generation.
- Keep output reviewable and approval-gated.

### V96 — Approval-Gated Platform Module Integration (Tentative)

Goal: Allow approved generated modules to be integrated into the AI Software Factory platform through controlled review and approval workflows.

Success direction:

- Prepare integration plan for generated modules.
- Require explicit operator approval before integration.
- Preserve rollback and audit trail.
- Prevent direct production mutation without approval.

### V97 — Module Migration & Data Contract Planner (Tentative)

Goal: Generate and validate database migrations, schema contracts, and module data boundaries before integration.

Success direction:

- Propose schema/data contract changes before implementation.
- Validate migration risks and compatibility.
- Require approval before migration materialization.
- Keep production data protected.

### V98 — Real Data Sandbox Seeding & Validation (Tentative)

Goal: Validate generated modules against realistic seeded data in isolated environments before rollout.

Success direction:

- Seed sandbox with realistic non-sensitive data.
- Validate module behavior against real workflow scenarios.
- Capture failures for repair proposal generation.
- Prevent generated module access to production data unless explicitly approved later.

### V99 — Production Readiness Gate for Generated Modules (Tentative)

Goal: Require automated validation, safety checks, testing evidence, repair history, and operator approval before any generated module becomes rollout-eligible.

Success direction:

- Aggregate tests, safety checks, smoke results, and repair history.
- Produce production-readiness evidence.
- Block rollout unless all required gates pass.
- Keep approval explicit and auditable.

### V100 — Approval-Gated Platform Feature Rollout (Tentative)

Goal: Enable the platform to deploy approved self-generated features into the product through a controlled, auditable rollout process.

Success direction:

- Roll out approved generated modules only after readiness gates pass.
- Maintain rollback and audit records.
- Track deployed module version and source generation run.
- Preserve production safety and operator control.

Long-term direction:

Generate -> Review -> Preview -> Test -> Self-Heal -> Re-Test -> Approve -> Integrate -> Validate Real Data -> Roll Out.

---

## Not Done Yet / Focused Future Work

Active focused future work:

- V88 — Real DB-preview file generation from browser app-build sessions.

Deferred product development until after the V88-V94 roadmap advances or the user approves scope expansion:

- Drag-and-drop app builder.
- Marketplace, templates, and plugins.
- Multi-user product/team layer beyond minimum admin/private beta access.
- External deployment/export connectors.
- Advanced workflow builder.
- Billing/customer onboarding.

---

## Next Chat Startup Instructions

When continuing in a new chat, start by verifying the latest `main` branch and this file.

Required first commands:

    cd /Users/toniteh/Desktop/ai-app-builder-dev
    git checkout main
    git pull origin main
    git log --oneline -5
    grep -n "Current Handover Snapshot\|Project Working Rule\|Active Next Milestone\|Post-V87 Roadmap\|V88" docs/PROJECT_MILESTONE_PLAN.md
    git status

Then proceed with the active next milestone:

1. V88 — Real DB-Preview File Generation From Browser App Build.

Do not start V89 or later until V88 is complete and merged, unless the user explicitly changes the roadmap.

Recommended V88 first steps:

- Inspect GitHub `main` and `docs/PROJECT_MILESTONE_PLAN.md`.
- Confirm V88 goal and safety boundaries.
- Inspect the app-build run path and generated-file persistence services.
- Add or update a V88 smoke check that verifies generated file records are created while `disk_write_performed=false` and `generated_code_execution_performed=false`.
- Keep `HOSTED_SANDBOX_PROVIDER=local_only`.

---

## Standard Validation Reminder

Every future milestone or operational change should continue to include:

- Syntax check.
- Specific smoke check.
- Safety-boundary verification.
- Secret-exposure check where deployment or environment config is involved.
- Function registry check for internal module/function breakage where relevant.
- Rendered dashboard JavaScript syntax check with `node --check` whenever `APP_BUILD_DASHBOARD_HTML` changes.
