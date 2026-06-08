# AI Software Factory — Project Milestone Plan

# Current Handover Snapshot

Repository: `tehkst/ai-app-builder-dev`

Current merged baseline after PR #107: `88bcc1c V80 — Internal Dogfooding Milestone (#107)`

Current completed milestone: V80 — Internal Dogfooding Milestone

Current active next milestone: MVP Launch Readiness Plan — pending user approval

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

Current safety boundary:

Controlled runtime execution, runtime log capture, classification-only runtime failure analysis, plan-only repair plan generation, approval-only repair gating, approval-gated sandbox repair execution, re-run-after-repair coordination, first self-healing loop coordination, request-tracking-only self-build module requests, gate-only module rollout approval/rejection, and demonstration-only internal dogfooding module flow are now implemented for approved runtime plans inside the approved sandbox only. No post-V80 milestone is approved yet. The next approved work should be a fixed MVP launch readiness plan with explicit user approval before any new numbered milestone is inserted or started.

---

This file is the source of truth for the current development roadmap.

## Planning Rule

Do not insert, rename, reorder, or replace milestones without explicit user confirmation.

If a new milestone is useful, add it first under **Optional / Backlog Milestones** and explain why it may be needed. Only move it into the active roadmap after approval.

Before adding any new milestone after V80, prepare an MVP Launch Readiness Plan that lists the exact remaining milestones needed to deploy a usable MVP on Railway or Gcore, the expected launch scope, safety boundaries, and the current gap from production. The user must explicitly approve that plan before coding continues.

## Project Working Rule

Use the direct GitHub connection for every step the assistant can safely handle, including repository inspection, branch creation, file creation, file updates, commits, PR creation, PR updates, PR review/status inspection, and PR merging.

Only involve the local Mac workflow when direct GitHub access cannot perform the step or when local validation is required. The user's local role should normally be limited to `git pull` / branch sync, running validation commands, pasting terminal output, and resolving local environment issues.

Do not ask for VS Code/manual file editing unless the user explicitly requests it. Prefer GitHub-side commits and PRs first, then local sync/test.

---

## Current Completed Milestone

### V80 — Internal Dogfooding Milestone

Status: Completed and merged via PR #107.

V80 added a demonstration-only internal dogfooding module service, API endpoints, dashboard controls, and smoke check. It can create and link a safe internal module request, inspect V77 self-healing handoff and V79 rollout-gate status, and record rollout approval/rejection decisions. V80 does not deploy, execute rollout, write generated files, write production files, modify live modules, start runtimes, install packages, auto-approve, bypass approvals, apply repairs, or restore files.

## Active Next Milestone

### MVP Launch Readiness Plan — pending user approval

Status: Planning required before further numbered milestones.

Goal: define the exact remaining milestones needed to launch a usable MVP on Railway or Gcore. The plan must decide whether the current product is launchable as an internal/demo MVP now, what is missing for a customer-facing MVP, what infra/provider should be used first, and which post-V80 milestones are required. No V81 or later milestone is approved until the user approves the fixed launch roadmap.

---

## Handover Update After V80

Current merged baseline:

```text
88bcc1c V80 — Internal Dogfooding Milestone (#107)
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

Current product limitation:

The system can now generate files, detect runtime readiness, build a run plan, require runtime approval, write approved files to the sandbox, start an approved sandbox runtime, capture runtime stdout/stderr/exit logs, classify runtime failures, generate repair plans, approve or reject repair plans, check repair apply gates, execute approved sandbox-bound repair operations, re-run after successful repair, compare before/after runtime status/log metadata, coordinate the first approval-preserving self-healing loop, track self-build module requests, gate module rollout eligibility/approval/rejection, and demonstrate one safe internal dogfooding module path. The exact launch path is not approved yet.

---

## MVP Launch Readiness — Draft for User Approval

Current answer: the project is not ready for a public customer-facing MVP yet, but it is close to an internal/demo MVP.

Minimum internal/demo MVP target:

- Deploy the platform backend/dashboard to a hosted environment.
- Let an admin create a small app/module request.
- Generate/review files through the existing safe review flow.
- Materialize only into an approved sandbox workspace.
- Run only approved sandbox runtime plans.
- Capture logs, analyze failures, propose repairs, approve repairs, apply sandbox-only repairs, and re-run.
- Show rollout eligibility and dogfooding decision state without production rollout.

Minimum public/customer MVP target:

- Persistent database/storage instead of in-memory milestone state.
- Real authentication and tenant/user boundary.
- Deployment environment hardening.
- Background job queue for long-running build/run/repair steps.
- Observability, error tracking, and audit logs.
- Environment variable/secrets management.
- Rate limits and abuse prevention.
- Clear sandbox resource limits.
- Billing/customer onboarding can remain out of first technical MVP if this is a private beta.

Recommended fixed remaining launch milestones, pending approval:

| Proposed Milestone | Name | Purpose |
|---|---|---|
| V81 | Production Config & Healthcheck | Add deployment-safe settings, health endpoint, startup validation, provider env docs |
| V82 | Persistent State Store | Replace in-memory approval/request/rollout state with database-backed persistence |
| V83 | Auth & Admin Access Gate | Add minimum admin login/API gate suitable for hosted MVP |
| V84 | Background Job Runner | Move long-running build/run/repair operations into tracked jobs instead of request-bound actions |
| V85 | Hosted Sandbox Boundary | Define provider-safe sandbox paths, resource limits, cleanup, and no-production-write guard |
| V86 | Deployment Pack for Railway/Gcore | Add Dockerfile/Procfile/provider config, env template, deploy guide, smoke checks |
| V87 | End-to-End MVP Launch Smoke | Validate full hosted flow from request to sandbox run, repair, re-run, and gated rollout decision |

Provider recommendation for first launch:

- Railway first for fastest MVP deployment, simpler GitHub-based deploys, PostgreSQL add-on, environment variable management, and quick rollback.
- Gcore later when the app needs more controlled infrastructure, regional/security choices, or heavier sandbox isolation.

Decision needed from user:

Approve the fixed V81-V87 launch roadmap above, edit it, or choose a different deployment-first roadmap. No coding should continue until this is approved.

---

## Not Done Yet / Focused Future Work

Focused pending areas:

- MVP launch readiness plan approval.
- Hosted deployment preparation.
- Persistent storage.
- Authentication/admin access.
- Background jobs.
- Hosted sandbox hardening.

Deferred until after MVP launch readiness:

- Drag-and-drop app builder.
- Marketplace, templates, and plugins.
- Multi-user product/team layer.
- External deployment/export connectors.
- Advanced workflow builder.

---

## Next Chat Startup Instructions

When continuing in a new chat, start by verifying the latest `main` branch and this file.

Required first commands:

    cd /Users/toniteh/Desktop/ai-app-builder-dev
    git checkout main
    git pull origin main
    git log --oneline -5
    grep -n "Current Handover Snapshot\|Project Working Rule\|Active Next Milestone\|MVP Launch Readiness" docs/PROJECT_MILESTONE_PLAN.md
    git status

Then do not start a new numbered milestone until the user approves a fixed post-V80 MVP launch roadmap.

---

## Standard Validation Reminder

Every milestone should continue to include:

- Syntax check.
- Milestone-specific smoke check.
- Previous browser-stage smoke checks where relevant.
- Function registry check for internal module/function breakage.
- Dependency warning check for dependency/package/deprecation warnings.
