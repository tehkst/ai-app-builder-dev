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

