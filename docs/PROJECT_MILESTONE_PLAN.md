# AI Software Factory — Project Milestone Plan

# Current Handover Snapshot

Repository: `tehkst/ai-app-builder-dev`

Current merged baseline after PR #116: `c980dcc V87 — End-to-End MVP Launch Smoke (#116)`

Current completed milestone: V87 — End-to-End MVP Launch Smoke

Current active next milestone: None. The approved V80-V87 roadmap is complete.

Current project status: Ready for private MVP deployment setup.

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
- V82 — persistent state store. Complete.
- V83 — auth and admin access gate. Complete.
- V84 — background job runner. Complete.
- V85 — hosted sandbox boundary. Complete.
- V86 — Railway/Gcore deployment pack. Complete.
- V87 — end-to-end MVP launch smoke. Complete.

Current safety boundary:

Controlled runtime execution, runtime log capture, classification-only runtime failure analysis, plan-only repair plan generation, approval-only repair gating, approval-gated sandbox repair execution, re-run-after-repair coordination, first self-healing loop coordination, request-tracking-only self-build module requests, gate-only module rollout approval/rejection, demonstration-only internal dogfooding module flow, readiness-only production config/healthcheck inspection, persistent state inspection, admin access gating, background job readiness inspection, hosted sandbox boundary checking, deployment-pack file/config validation, and final end-to-end MVP launch-readiness smoke aggregation are implemented. The repository is ready for private MVP deployment setup only. Do not create V88 or continue milestone development without explicit user approval for a new roadmap.

---

This file is the source of truth for the current development roadmap.

## Planning Rule

Do not insert, rename, reorder, or replace milestones without explicit user confirmation.

The post-V80 MVP launch roadmap V81-V87 is complete. Do not create V88 or any extra milestone until the user approves a new roadmap.

## Project Working Rule

Use the direct GitHub connection for every step the assistant can safely handle, including repository inspection, branch creation, file creation, file updates, commits, PR creation, PR updates, PR review/status inspection, and PR merging.

Only involve the local Mac workflow when direct GitHub access cannot perform the step or when local validation is required. The user's local role should normally be limited to `git pull` / branch sync, running validation commands, pasting terminal output, and resolving local environment issues.

Do not ask for VS Code/manual file editing unless the user explicitly requests it. Prefer GitHub-side commits and PRs first, then local sync/test.

---

## Current Completed Milestone

### V87 — End-to-End MVP Launch Smoke

Status: Completed and merged via PR #116.

V87 added the final end-to-end MVP launch smoke aggregator and launch-readiness report. It aggregates V81 production config and healthcheck readiness, V84 background job runner readiness, V85 hosted sandbox boundary contract, and V86 Railway/Gcore deployment pack completeness. The final local smoke returned `passed=True` and `launch_readiness_status=ready_for_private_mvp_deployment_setup` while preserving no-deployment, no-runtime, no-generated-execution, no-secret-write, no-public-URL, no-approval-bypass, no-repair, no-restore, and no-rollout safety flags.

## Active Next Milestone

None.

The approved V80-V87 roadmap is complete. Next work should be treated as a new explicitly approved operational plan or a new explicitly approved development roadmap.

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

## Handover Update After V87

Current merged baseline:

```text
c980dcc V87 — End-to-End MVP Launch Smoke (#116)
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

The system can generate files, detect runtime readiness, build a run plan, require runtime approval, write approved files to the sandbox, start an approved sandbox runtime, capture runtime stdout/stderr/exit logs, classify runtime failures, generate repair plans, approve or reject repair plans, check repair apply gates, execute approved sandbox-bound repair operations, re-run after successful repair, compare before/after runtime status/log metadata, coordinate the first approval-preserving self-healing loop, track self-build module requests, gate module rollout eligibility/approval/rejection, demonstrate one safe internal dogfooding module path, inspect production readiness/configuration without exposing secrets, persist key platform state, gate admin access, inspect background job readiness, preserve hosted sandbox boundaries, provide Railway/Gcore deployment-preparation files, and aggregate final private MVP launch-readiness.

---

## Not Done Yet / Focused Future Work

Operational work after V87, requiring explicit approval before starting:

- Railway project setup.
- PostgreSQL provisioning.
- Production environment secret configuration.
- Private MVP `/health` verification.
- Private MVP admin login verification.
- Private MVP smoke review.
- Gcore evaluation if Railway is not sufficient.

Deferred product development until after a new roadmap is approved:

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
    grep -n "Current Handover Snapshot\|Project Working Rule\|Active Next Milestone\|Completed MVP Launch Roadmap\|Handover Update After V87" docs/PROJECT_MILESTONE_PLAN.md
    git status

Then decide one of these explicitly approved next paths:

1. Operational private MVP deployment setup using the V86 deployment pack.
2. A new post-V87 development roadmap.

Do not start V88 or any additional milestone unless the user explicitly approves a new roadmap.

Recommended first operational path:

- Railway private MVP setup.
- Attach PostgreSQL.
- Configure production env secrets from `.env.example`.
- Keep `HOSTED_SANDBOX_PROVIDER=local_only`.
- Verify `/health`.
- Verify admin login/API gate.
- Run private MVP smoke review.

---

## Standard Validation Reminder

Every future milestone or operational change should continue to include:

- Syntax check.
- Specific smoke check.
- Safety-boundary verification.
- Secret-exposure check where deployment or environment config is involved.
- Function registry check for internal module/function breakage where relevant.
