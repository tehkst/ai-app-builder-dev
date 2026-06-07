# AI Software Factory — Project Milestone Plan

# Current Handover Snapshot

Repository: `tehkst/ai-app-builder-dev`

Current merged baseline after PR #90: `b5e5bff Refocus roadmap on self-building runtime loop (#90)`

Current completed milestone: V66 — Browser Manual Test Harness Panel

Current active next milestone: V67 — Runtime Readiness Detector

Primary product direction:

Build the minimum self-building and self-healing app factory loop:

Generate app/module files -> write approved files to sandbox -> run approved app in sandbox -> capture logs/errors -> analyze failure -> propose repair -> approve repair -> apply repair -> re-run -> roll out passing module.

Near-term checkpoints:

- V70 — first controlled sandbox app run.
- V77 — first complete self-healing loop.
- V80 — first self-built module rollout.

Current safety boundary:

Runtime execution is still not implemented. V67 must only detect runtime readiness and produce planning metadata. It must not install packages, start servers, execute generated code, apply repairs, or execute restores.

---

This file is the source of truth for the current development roadmap.

## Planning Rule

Do not insert, rename, reorder, or replace milestones without explicit user confirmation.

If a new milestone is useful, add it first under **Optional / Backlog Milestones** and explain why it may be needed. Only move it into the active roadmap after approval.

---

## Current Baseline

Repository: `tehkst/ai-app-builder-dev`

Current confirmed merged baseline:

| Milestone | Name | Status | PR |
|---|---|---:|---:|
| V42.1 | Restore Target Content Preview | Complete | #49 |
| V43 | Safe DB Restore Execution Engine | Complete | #50 |
| V44 | Restore Result Record / Audit Trail | Complete | #51 |
| V45 | Post-Restore Snapshot Creation | Complete | #52 |
| V46 | Restore Rollback Safety | Complete | #53 |
| Extra UI | Restore Snapshot Timeline Labels | Complete | #54 |

---

## Historical Backend Safety Stage

| Milestone | Name | Status |
|---|---|---:|
| V43 | Safe DB Restore Execution Engine | Complete |
| V44 | Restore Result Record / Audit Trail | Complete |
| V45 | Post-Restore Snapshot Creation | Complete |
| V46 | Restore Rollback Safety | Complete |
| V47 | Filesystem Write Guard / Path Guard | Complete |

---

## Historical Browser UI Stage

| Milestone | Name | Status |
|---|---|---:|
| V48 | Browser Restore Control Panel | Complete |
| V49 | Browser Workspace File Editor | Complete |
| V50 | Browser App Builder Workspace | Complete |
| V51 | Browser Preview / Run Panel | Complete |
| V52 | Browser Self-Healing Console | Complete |
| V53 | Browser One-Click Repair Flow | Complete |

---

## Optional / Backlog Milestones

### V48A — Restore Execution Timeline API

Status: Optional / Not approved for active roadmap yet.

Purpose:
Create a backend API/service that returns a unified restore timeline for a generated file.

It may combine:
- normal version snapshots
- pre-restore rollback snapshots
- restored target versions
- post-restore result snapshots
- restore execution audit records

Reason it may be useful:
The browser restore control panel may eventually need a clean backend timeline endpoint instead of assembling restore history from separate version and audit APIs.

Current decision:
Do not implement yet. Reconsider during V48 Browser Restore Control Panel if the UI needs this backend support.

---

## Current Completed Milestone

### V66 — Browser Manual Test Harness Panel

Status: Completed and merged via PR #88.

V66 added a browser dashboard panel for the V65 manual browser test harness. The panel shows selected-file status, safety mode, and manual-open instructions for sandbox-written static HTML files while preserving the no-server-startup, no-generated-code-execution, no-package-command, no-repair, and no-restore safety boundaries.

## Active Next Milestone

### V67 — Runtime Readiness Detector

Status: Active next milestone.

Goal: inspect generated app/module files and determine whether they are runnable, what framework/runtime they use, what command would run them, what port they need, and what approvals are required. V67 is detection/planning only: it must not install packages, start servers, execute generated code, apply repairs, or restore files.


---

## Handover Update After V60

Current merged baseline:

```text
7470aa0 Add materialization approval history (#76)
```

Completed browser milestones after the original roadmap:

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

Earlier completed foundation milestones:

| Milestone | Name | Status |
|---|---|---:|
| V1 | Initial Project Foundation | Complete |
| V2 | Core Graph / Dependency Guard / Template Enforcer | Complete |
| V3 | Generated Backend Template Foundation | Complete |
| V4 | Runtime Validation and Repair Loop Foundation | Complete |
| V5 | Platform Foundation / Workspace / Tenant / Persistence / API / Approval Base | Complete |

Current product limitation:

The system now has a safe static preview renderer, approval-gated materialization planning, browser-visible approval history, backend-persisted approval records, a blocked execution gate, an approved local sandbox writer, and a manual browser harness for sandbox-written static HTML files. Runtime app execution is still not implemented.

---

## Not Done Yet / Focused Future Work

The project should now avoid broad feature expansion until the self-building/self-healing loop is working.

Focused pending areas:

- Runtime readiness detection.
- Runtime run-plan generation.
- Runtime approval gate.
- Controlled sandbox app execution.
- Runtime preview and stop control.
- Runtime logs and error capture.
- AI runtime failure analysis.
- Approval-gated repair planning and application.
- Re-run after repair.
- Self-built module rollout.

Deferred until after the loop works:

- Drag-and-drop app builder.
- Marketplace, templates, and plugins.
- Multi-user product/team layer.
- External deployment/export connectors.
- Advanced workflow builder.

---

## Completed Materialization Milestones

### V63 — Safe Workspace Materialization Dry Run

Goal:

Create a safe dry-run materialization preview that converts DB-backed generated files into a clear would-write plan without writing files to disk. This milestone bridges the blocked V62 execution gate and a future approved sandbox workspace writer.

Expected output:

- Backend dry-run materialization service for selected DB-backed generated files.
- API endpoint or service helper to generate a would-write file plan without executing materialization.
- Browser section shows dry-run target paths, file count, approval/gate context, and blocked execution status.
- Dry-run result clearly states that no files were written and no generated code was executed.
- Existing V62 execution gate, V61 persistent approval record, V60 approval history, V59 approval workflow, V58 materialization plan, V57 static preview, V56 results review, V55 specification builder, and V54 launcher preserved.
- Smoke check for dry-run materialization markers.
- Fast release gate passes.

Safety requirements:

- No generated-code execution.
- No runtime server.
- No preview server startup.
- No filesystem writes.
- No generated files outside DB preview.
- Dry-run plan only; no materialization execution.
- Persistent approval record must not automatically trigger materialization.
- No automatic repair application.
- No restore execution.

---

## Recommended Roadmap Toward Self-Building and Self-Healing App Factory

## Primary Product Direction

The main objective is to build a live self-building and self-healing app factory.

The platform should become capable of generating small app modules, writing them into a controlled sandbox, running them only after explicit approval, observing runtime failures, planning repairs, applying approved repairs, and re-running until the module works.

The near-term priority is not to manually build every product feature. The priority is to build the loop that lets the app safely build, test, repair, and roll out modules.

Target checkpoints:

- Reach first controlled sandbox app run by V70.
- Reach first self-healing repair loop by V77.
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
| V67 | Runtime Readiness Detector | Detect runnable app/module type, scripts, ports, package manager, env needs, and required approvals |
| V68 | Runtime Run Plan Builder | Build exact install/run/port plan without executing generated code |
| V69 | Runtime Approval Gate | Require explicit approval before first controlled sandbox run |
| V70 | First Controlled Sandbox App Run | Start an approved generated app in the controlled sandbox |
| V71 | Runtime Preview and Stop Control | Show running app status/preview URL and provide safe stop control |
| V72 | Runtime Log and Error Capture | Capture stdout/stderr/startup/browser-visible runtime failures |
| V73 | AI Runtime Failure Analyzer | Analyze captured errors/logs and identify likely causes |
| V74 | Repair Plan Generator | Propose exact file changes without applying them |
| V75 | Approval-Gated Repair Apply | Apply approved repair changes only after user approval |
| V76 | Re-run After Repair | Re-run repaired app and compare before/after result |
| V77 | First Self-Healing Loop | Complete run, error, repair plan, approval, repair, and re-run |
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
    grep -n "Current Handover Snapshot\|Active Next Milestone\|V67 — Runtime Readiness Detector\|V70\|V77\|V80" docs/PROJECT_MILESTONE_PLAN.md
    git status

Then begin only the active next milestone:

V67 — Runtime Readiness Detector

Before coding V67, inspect:

    grep -n "class PlatformGeneratedFile\|workflow_run_id\|workspace_id\|project_id" app/platform/persistence/models.py | sed -n '1,220p'
    grep -n "generated-files\|workspace\|safe-static-preview\|manual-browser-test-harness" app/platform/api/app_build_routes.py | sed -n '1,260p'
    sed -n '1,260p' app/platform/persistence/models.py
    sed -n '2500,2905p' app/platform/api/app_build_routes.py
    sed -n '1,240p' app/platform/agents/manual_browser_test_harness_check.py

V67 must remain detection/planning only.

---

## Standard Validation Reminder

Every milestone should continue to include:

- Syntax check.
- Milestone-specific smoke check.
- Previous browser-stage smoke checks where relevant.
- Function registry check for internal module/function breakage.
- Dependency warning check for dependency/package/deprecation warnings.
- Fast release gate.
