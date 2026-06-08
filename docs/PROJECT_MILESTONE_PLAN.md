# AI Software Factory — Project Milestone Plan

# Current Handover Snapshot

Repository: `tehkst/ai-app-builder-dev`

Current merged baseline after PR #109: `954c764 V81 — Production Config & Healthcheck (#109)`

Current completed milestone: V81 — Production Config & Healthcheck

Current active next milestone: V82 — Persistent State Store

Primary product direction:

Build the minimum self-building and self-healing app factory loop:

Generate app/module files -> write approved files to sandbox -> run approved app in sandbox -> capture logs/errors -> analyze failure -> propose repair -> approve repair -> apply repair -> re-run -> roll out passing module.

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
- V82 — persistent state store.
- V83 — auth and admin access gate.
- V84 — background job runner.
- V85 — hosted sandbox boundary.
- V86 — Railway/Gcore deployment pack.
- V87 — end-to-end MVP launch smoke.

Current safety boundary:

Controlled runtime execution, runtime log capture, classification-only runtime failure analysis, plan-only repair plan generation, approval-only repair gating, approval-gated sandbox repair execution, re-run-after-repair coordination, first self-healing loop coordination, request-tracking-only self-build module requests, gate-only module rollout approval/rejection, demonstration-only internal dogfooding module flow, and readiness-only production config/healthcheck inspection are now implemented for approved runtime plans inside the approved sandbox only. V81-V87 are approved as the fixed MVP launch roadmap. Do not insert, rename, reorder, or replace these milestones without explicit user approval.

---

This file is the source of truth for the current development roadmap.

## Planning Rule

Do not insert, rename, reorder, or replace milestones without explicit user confirmation.

The post-V80 MVP launch roadmap is approved as V81-V87. Work one milestone at a time. Do not create V88 or any extra milestone until V87 is completed and the user approves the next roadmap.

## Project Working Rule

Use the direct GitHub connection for every step the assistant can safely handle, including repository inspection, branch creation, file creation, file updates, commits, PR creation, PR updates, PR review/status inspection, and PR merging.

Only involve the local Mac workflow when direct GitHub access cannot perform the step or when local validation is required. The user's local role should normally be limited to `git pull` / branch sync, running validation commands, pasting terminal output, and resolving local environment issues.

Do not ask for VS Code/manual file editing unless the user explicitly requests it. Prefer GitHub-side commits and PRs first, then local sync/test.

---

## Current Completed Milestone

### V81 — Production Config & Healthcheck

Status: Completed and merged via PR #109.

V81 added a readiness-only production config service, upgraded hosted health endpoints, added admin-gated platform config readiness/checklist endpoints, populated `.env.example` with placeholders only, and added a production config smoke check. It can inspect required and optional deployment environment variables by configured true/false only, report missing required environment names, return Railway-first and Gcore provider checklist guidance, and prove safety flags for no deployment, runtime execution, generated code execution, generated file writes, production file writes, live module modification, package installation, auto approval, approval bypass, repair application, restore execution, or rollout execution.

## Active Next Milestone

### V82 — Persistent State Store

Status: Active next milestone.

Goal: replace remaining in-memory approval/request/rollout state with database-backed persistence suitable for hosted private MVP operation. V82 must preserve approval gates and safety boundaries. It must not deploy, start runtimes outside approved gates, execute generated code without approval, write generated files without approval, modify live modules, auto-approve, bypass approvals, apply unapproved repairs, restore files, or execute rollouts.

Expected output:

- Inventory of remaining in-memory state stores.
- Database-backed persistence for approval/request/rollout state needed for private MVP continuity.
- Safe read/write APIs that preserve existing approval gates.
- Migration/table creation updates where needed.
- V82 smoke check proving persistence survives fresh service instances and does not bypass approvals.

---

## Approved MVP Launch Roadmap

| Milestone | Name | Purpose | Status |
|---|---|---|---:|
| V81 | Production Config & Healthcheck | Add deployment-safe settings, health endpoint, startup validation, provider env docs | Complete |
| V82 | Persistent State Store | Replace in-memory approval/request/rollout state with database-backed persistence | Active next |
| V83 | Auth & Admin Access Gate | Add minimum admin login/API gate suitable for hosted MVP | Pending |
| V84 | Background Job Runner | Move long-running build/run/repair operations into tracked jobs instead of request-bound actions | Pending |
| V85 | Hosted Sandbox Boundary | Define provider-safe sandbox paths, resource limits, cleanup, and no-production-write guard | Pending |
| V86 | Deployment Pack for Railway/Gcore | Add Dockerfile/Procfile/provider config, env template, deploy guide, smoke checks | Pending |
| V87 | End-to-End MVP Launch Smoke | Validate full hosted flow from request to sandbox run, repair, re-run, and gated rollout decision | Pending |

Provider decision:

- Railway first for fastest MVP deployment, simpler GitHub-based deploys, PostgreSQL add-on, environment variable management, and quick rollback.
- Gcore later if the app needs more controlled infrastructure, regional/security choices, or heavier sandbox isolation.

Launch target after V87:

- Production-ready private MVP / closed beta, not broad public SaaS.
- Admin-only access acceptable for the first launch.
- Billing, marketplace, multi-tenant team features, and advanced external deployment connectors remain out of scope until after V87.

---

## Handover Update After V81

Current merged baseline:

```text
954c764 V81 — Production Config & Healthcheck (#109)
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

Current product limitation:

The system can now generate files, detect runtime readiness, build a run plan, require runtime approval, write approved files to the sandbox, start an approved sandbox runtime, capture runtime stdout/stderr/exit logs, classify runtime failures, generate repair plans, approve or reject repair plans, check repair apply gates, execute approved sandbox-bound repair operations, re-run after successful repair, compare before/after runtime status/log metadata, coordinate the first approval-preserving self-healing loop, track self-build module requests, gate module rollout eligibility/approval/rejection, demonstrate one safe internal dogfooding module path, and inspect production readiness/configuration without exposing secrets. V82-V87 must now convert this into a hosted, persistent, admin-gated private MVP.

---

## Not Done Yet / Focused Future Work

Focused pending areas before private MVP launch:

- Persistent storage.
- Authentication/admin access.
- Background jobs.
- Hosted sandbox hardening.
- Railway/Gcore deployment pack.
- End-to-end hosted MVP launch smoke.

Deferred until after V87:

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
    grep -n "Current Handover Snapshot\|Project Working Rule\|Active Next Milestone\|Approved MVP Launch Roadmap\|V82 — Persistent State Store" docs/PROJECT_MILESTONE_PLAN.md
    git status

Then begin only the active next milestone:

V82 — Persistent State Store

Before coding V82, inspect:

    find app -maxdepth 4 -type f \( -name "*.py" -o -name "*.env*" \) | sort | sed -n '1,260p'
    grep -R "in-memory\|memory\|dict\|store\|approval\|request\|rollout\|State\|Base\|Column" -n app/platform app/api | sed -n '1,320p'
    ls -la

V82 must add persistent state store only. It must preserve all approval gates and must not deploy, start runtimes outside approved gates, write generated files without approval, execute generated code without approval, modify live modules, auto-approve, bypass approvals, apply unapproved repairs, restore files, or execute rollouts.

---

## Standard Validation Reminder

Every milestone should continue to include:

- Syntax check.
- Milestone-specific smoke check.
- Previous browser-stage smoke checks where relevant.
- Function registry check for internal module/function breakage.
