# AI Software Factory — Project Milestone Plan

# Current Handover Snapshot

Repository: `tehkst/ai-app-builder-dev`

Current merged baseline after PR #93: `54707bd V68 — Runtime Run Plan Builder (#93)`

Current completed milestone: V68 — Runtime Run Plan Builder

Current active next milestone: V69 — Runtime Approval Gate

Primary product direction:

Build the minimum self-building and self-healing app factory loop:

Generate app/module files -> write approved files to sandbox -> run approved app in sandbox -> capture logs/errors -> analyze failure -> propose repair -> approve repair -> apply repair -> re-run -> roll out passing module.

Near-term checkpoints:

- V70 — first controlled sandbox app run.
- V77 — first complete self-healing loop.
- V80 — first self-built module rollout.

Current safety boundary:

Runtime execution is still not implemented. V69 must add an explicit approval gate for a runtime run plan before any future controlled sandbox run. It must not install packages, start servers, execute generated code, apply repairs, write generated files, or execute restores.

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

### V68 — Runtime Run Plan Builder

Status: Completed and merged via PR #93.

V68 added a planning-only runtime run plan builder for DB-backed generated files. It converts V67 readiness output into exact planned install and run steps, working directory, port, environment requirements, approval requirements, blocking reasons, and explicit safety flags. It also added dashboard controls and a smoke check while preserving the no-package-install, no-server-start, no-generated-code-execution, no-generated-file-write, no-repair, and no-restore boundaries.

## Active Next Milestone

### V69 — Runtime Approval Gate

Status: Active next milestone.

Goal: add an explicit approval gate for runtime run plans before any future sandbox runtime execution. V69 should persist or represent approval/rejection state for a specific run plan and expose safe API/dashboard controls to approve, reject, and inspect approval status. V69 is still gate-only: it must not install packages, start servers, execute generated code, write generated files, apply repairs, or restore files.

---

## Handover Update After V68

Current merged baseline:

```text
54707bd V68 — Runtime Run Plan Builder (#93)
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

Current product limitation:

The system now has safe static previews, approval-gated materialization planning, browser-visible approval history, backend-persisted approval records, a blocked execution gate, an approved local sandbox writer, a manual browser harness for sandbox-written static HTML files, runtime readiness detection, and runtime run-plan generation. Runtime app execution is still not implemented.

---

## Not Done Yet / Focused Future Work

The project should now avoid broad feature expansion until the self-building/self-healing loop is working.

Focused pending areas:

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
| V67 | Runtime Readiness Detector | Complete — detect runnable app/module type, scripts, ports, package manager, env needs, and required approvals |
| V68 | Runtime Run Plan Builder | Complete — build exact install/run/port plan without executing generated code |
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
    grep -n "Current Handover Snapshot\|Project Working Rule\|Active Next Milestone\|V69 — Runtime Approval Gate\|V70\|V77\|V80" docs/PROJECT_MILESTONE_PLAN.md
    git status

Then begin only the active next milestone:

V69 — Runtime Approval Gate

Before coding V69, inspect:

    grep -n "runtime-run-plan\|Runtime Run Plan Builder\|build_runtime_run_plan" app/platform/api/app_build_routes.py | sed -n '1,260p'
    sed -n '1,260p' app/platform/services/runtime_run_plan_builder_service.py
    sed -n '1,220p' app/platform/agents/runtime_run_plan_builder_check.py

V69 must remain gate-only and must not perform runtime execution.

---

## Standard Validation Reminder

Every milestone should continue to include:

- Syntax check.
- Milestone-specific smoke check.
- Previous browser-stage smoke checks where relevant.
- Function registry check for internal module/function breakage.
- Dependency warning check for dependency/package/deprecation warnings.
