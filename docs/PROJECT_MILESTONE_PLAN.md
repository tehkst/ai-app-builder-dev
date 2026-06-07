# AI Software Factory — Project Milestone Plan

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

## Backend Safety Stage

| Milestone | Name | Status |
|---|---|---:|
| V43 | Safe DB Restore Execution Engine | Complete |
| V44 | Restore Result Record / Audit Trail | Complete |
| V45 | Post-Restore Snapshot Creation | Complete |
| V46 | Restore Rollback Safety | Complete |
| V47 | Filesystem Write Guard / Path Guard | Next |

---

## Browser UI Stage

| Milestone | Name | Status |
|---|---|---:|
| V48 | Browser Restore Control Panel | Pending |
| V49 | Browser Workspace File Editor | Pending |
| V50 | Browser App Builder Workspace | Pending |
| V51 | Browser Preview / Run Panel | Pending |
| V52 | Browser Self-Healing Console | Pending |
| V53 | Browser One-Click Repair Flow | Pending |

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

## Active Next Milestone

### V47 — Filesystem Write Guard / Path Guard

Goal:
Before any future real filesystem write is enabled, add a strict guard layer that blocks unsafe paths and confirms generated file writes stay inside an approved workspace root.

Safety requirements:
- Block absolute paths unless explicitly approved.
- Block path traversal such as `../`.
- Block writes outside approved workspace root.
- Block dangerous system paths.
- Preserve current DB-preview-only generated file behavior.
- No real generated-code execution.
- No real filesystem writes in current restore flow.

Expected output:
- Path guard service.
- Guard check / smoke test.
- Release gate still passes.

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

Earlier completed foundation milestones:

| Milestone | Name | Status |
|---|---|---:|
| V1 | Initial Project Foundation | Complete |
| V2 | Core Graph / Dependency Guard / Template Enforcer | Complete |
| V3 | Generated Backend Template Foundation | Complete |
| V4 | Runtime Validation and Repair Loop Foundation | Complete |
| V5 | Platform Foundation / Workspace / Tenant / Persistence / API / Approval Base | Complete |

Current product limitation:

The system now has a safe static preview renderer, an approval-gated materialization plan, a browser UI-state approval workflow, a browser-visible approval history, backend-persisted approval records, and a blocked materialization execution gate for DB-backed generated files, but it does not yet write generated files to a workspace or run generated apps as live browser apps. Generated files remain DB-preview-only.

---

## Not Done Yet / Future Work

Major product areas still pending:

- Browser app creation UX.
- App specification / planning UX.
- Workflow builder.
- Drag-and-drop app builder.
- Real browser testing harness.
- Safe workspace materialization dry run.
- Approval-gated workspace materialization.
- Sandbox workspace writer.
- Static app export package.
- Deployment/export connectors.
- Multi-user product layer.
- Marketplace, templates, and plugins.

---

## Active Next Milestone After V62

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

## Recommended Roadmap Toward First Browser-Testable App

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
| V65 | Manual Browser Test Harness | Let user manually test a static generated app in controlled local mode |

---

## Standard Validation Reminder

Every milestone should continue to include:

- Syntax check.
- Milestone-specific smoke check.
- Previous browser-stage smoke checks where relevant.
- Function registry check for internal module/function breakage.
- Dependency warning check for dependency/package/deprecation warnings.
- Fast release gate.
