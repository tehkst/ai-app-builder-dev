# AI Software Factory — Project Milestone Plan

# Current Handover Snapshot

Repository: `tehkst/ai-app-builder-dev`

Current merged baseline after PR #104: `172c90d V77 — First Self-Healing Loop (#104)`

Current completed milestone: V77 — First Self-Healing Loop

Current active next milestone: V78 — Self-Build Module Request Flow

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
- V78 — self-build module request flow.
- V80 — first self-built module rollout.

Current safety boundary:

Controlled runtime execution, runtime log capture, classification-only runtime failure analysis, plan-only repair plan generation, approval-only repair gating, approval-gated sandbox repair execution, re-run-after-repair coordination, and first self-healing loop coordination are now implemented for approved runtime plans inside the approved sandbox only. V78 may add a self-build module request flow that captures and tracks small module build requests through the existing approved loop. V78 must not auto-approve repairs, auto-apply unapproved repairs, restore files, roll out modules, install packages beyond already approved runtime plans, or broaden runtime execution beyond the approved sandbox boundary.

---

This file is the source of truth for the current development roadmap.

## Planning Rule

Do not insert, rename, reorder, or replace milestones without explicit user confirmation.

If a new milestone is useful, add it first under **Optional / Backlog Milestones** and explain why it may be needed. Only move it into the active roadmap after approval.

## Project Working Rule

Use the direct GitHub connection for every step the assistant can safely handle, including repository inspection, branch creation, file creation, file updates, commits, PR creation, PR updates, PR review/status inspection, and PR merging.

Only involve the local Mac workflow when direct GitHub access cannot perform the step or when local validation is required. The user's local role should normally be limited to `git pull` / branch sync, running validation commands, pasting terminal output, and resolving local environment issues.

Do not ask for VS Code/manual file editing unless the user explicitly requests it. Prefer GitHub-side commits and PRs first, then local sync/test.

---

## Current Completed Milestone

### V77 — First Self-Healing Loop

Status: Completed and merged via PR #104.

V77 added the first approval-preserving self-healing loop coordinator. It connects runtime status/log capture, failure analysis, repair plan status, repair approval status, repair execution history, repair re-run history, and final loop outcome into one observable workflow. It can trigger only the existing V76 repair re-run path when repair approval and successful repair execution already exist. V77 does not auto-approve repairs, apply unapproved repairs, restore files, roll out modules, install packages during re-run, or create a new runtime execution path.

## Active Next Milestone

### V78 — Self-Build Module Request Flow

Status: Active next milestone.

Goal: let a user request a small internal module for the platform to build through the existing self-healing loop. V78 should capture the module request, normalize it into a safe build request record, expose request status/history in the dashboard/API, and hand off to existing app-build/self-healing workflow records without adding rollout behavior. V78 must preserve all approval gates. It must not auto-approve repairs, must not apply unapproved repairs, must not restore files, must not roll out modules, must not broaden runtime permissions, and must remain inside the approved sandbox runtime boundary.

---

## Handover Update After V77

Current merged baseline:

```text
172c90d V77 — First Self-Healing Loop (#104)
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

Current product limitation:

The system can now generate files, detect runtime readiness, build a run plan, require runtime approval, write approved files to the sandbox, start an approved sandbox runtime, capture runtime stdout/stderr/exit logs, classify runtime failures, generate repair plans, approve or reject repair plans, check repair apply gates, execute approved sandbox-bound repair operations, re-run after successful repair, compare before/after runtime status/log metadata, and coordinate the first approval-preserving self-healing loop. A user-facing self-build module request flow is not implemented yet and is the V78 focus.

---

## Not Done Yet / Focused Future Work

The project should now avoid broad feature expansion until the self-building/self-healing loop is working.

Focused pending areas:

- Self-build module request flow.
- Module rollout gate.
- First internal dogfooding module.

Deferred until after the loop works:

- Drag-and-drop app builder.
- Marketplace, templates, and plugins.
- Multi-user product/team layer.
- External deployment/export connectors.
- Advanced workflow builder.

---

## Recommended Roadmap Toward Self-Building and Self-Healing App Factory

## Primary Product Direction

The main objective is to build a live self-building and self-healing app factory.

The platform should become capable of generating small app modules, writing them into a controlled sandbox, running them only after explicit approval, observing runtime failures, planning repairs, applying approved repairs, and re-running until the module works.

The near-term priority is not to manually build every product feature. The priority is to build the loop that lets the app safely build, test, repair, and roll out modules.

Target checkpoints:

- First controlled sandbox app run reached by V70.
- Runtime log capture reached by V71.
- Runtime failure analysis reached by V72.
- Repair plan generation reached by V73.
- Repair approval gate reached by V74.
- Repair executor reached by V75.
- Re-run after repair reached by V76.
- First self-healing repair loop reached by V77.
- Reach first self-built module rollout by V80.

Minor V-number milestones may be inserted when implementation gaps are discovered, but every inserted milestone must belong to this self-building/self-healing direction, preserve existing safety boundaries unless explicitly expanded, include smoke/preservation checks, and be completed before the next milestone starts.

---

| Milestone | Name | Purpose |
|---|---|---|
| V54 | Browser App Build Session Launcher | Start app builds from a clean browser form |
| V55 | Browser App Spec Form / Prompt Builder | Convert user idea into clearer app requirements before generation |
| V56 | Browser App Build Results Review Panel | Review generated files, workflow status, and safety flags after app-build runs |
| V57 | Safe Static Preview Renderer | Render safe static HTML/CSS previews from DB content only |
| V58 | Approval-Gated Workspace Materialization Plan | Prepare file materialization plan but do not write files yet |
| V59 | Materialization Approval Workflow | Capture UI-state approval/rejection without granting write capability |
| V60 | Materialization Approval History | Show browser-visible approval history while remaining UI-state-only |
| V61 | Persistent Approval Record | Persist approval metadata in backend storage without granting execution |
| V62 | Materialization Execution Gate | Add blocked execution-attempt gate that checks approval state but performs no writes |
| V63 | Safe Workspace Materialization Dry Run | Produce a would-write workspace plan without writing generated files to disk |
| V64 | Local Sandbox Workspace Writer | Write generated files only into an approved sandbox path after explicit approval |
| V65 | Manual Browser Test Harness | Complete — backend harness for safe manual static browser testing |
| V66 | Browser Manual Test Harness Panel | Complete — browser UI for safe manual static harness instructions |
| V67 | Runtime Readiness Detector | Complete — detect runnable app/module type, scripts, ports, package manager, env needs, and required approvals |
| V68 | Runtime Run Plan Builder | Complete — build exact install/run/port plan without executing generated code |
| V69 | Runtime Approval Gate | Complete — require explicit approval before first controlled sandbox run |
| V70 | First Controlled Sandbox App Run | Complete — start an approved generated app in the controlled sandbox |
| V71 | Runtime Log Capture | Complete — capture stdout/stderr/startup/exit logs from controlled sandbox runtime |
| V72 | AI Runtime Failure Analyzer | Complete — analyze captured errors/logs and identify likely causes |
| V73 | Repair Plan Generator | Complete — propose exact file changes without applying them |
| V74 | Repair Approval Gate | Complete — approve/reject repair plan and block unapproved apply attempts |
| V75 | Approval-Gated Repair Executor | Complete — apply approved safe repair operations only inside the approved sandbox |
| V76 | Re-run After Repair | Complete — re-run repaired app and compare before/after result |
| V77 | First Self-Healing Loop | Complete — coordinate run, error, repair plan, approval, repair, and re-run |
| V78 | Self-Build Module Request Flow | Let user request a small module for the platform to build through the loop |
| V79 | Module Rollout Gate | Promote passing generated module only after approval and checks |
| V80 | Internal Dogfooding Milestone | Use the platform to build and roll out one real internal module |

---

## Next Chat Startup Instructions

When continuing in a new chat, start by verifying the latest `main` branch and this file.

Required first commands:

    cd /Users/toniteh/Desktop/ai-app-builder-dev
    git checkout main
    git pull origin main
    git log --oneline -5
    grep -n "Current Handover Snapshot\|Project Working Rule\|Active Next Milestone\|V78 — Self-Build Module Request Flow\|V80" docs/PROJECT_MILESTONE_PLAN.md
    git status

Then begin only the active next milestone:

V78 — Self-Build Module Request Flow

Before coding V78, inspect:

    sed -n '1,260p' app/platform/services/self_healing_loop_coordinator_service.py
    sed -n '1,260p' app/platform/services/app_build_orchestrator.py
    grep -n "self-healing-loop\|app-build\|workflowRunId\|startAppBuild" app/platform/api/app_build_routes.py | sed -n '1,460p'

V78 must add user-facing self-build module request flow only. It must not auto-approve repairs, apply unapproved repairs, execute restores, roll out modules, or broaden runtime execution beyond approved sandbox execution.

---

## Standard Validation Reminder

Every milestone should continue to include:

- Syntax check.
- Milestone-specific smoke check.
- Previous browser-stage smoke checks where relevant.
- Function registry check for internal module/function breakage.
- Dependency warning check for dependency/package/deprecation warnings.
