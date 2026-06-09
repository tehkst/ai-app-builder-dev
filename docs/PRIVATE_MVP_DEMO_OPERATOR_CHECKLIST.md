# Private MVP Demo Script & Operator Checklist

Repository: `tehkst/ai-app-builder-dev`

Milestone: V94 — Private MVP Demo Script & Operator Checklist

## Purpose

Provide a repeatable private MVP demonstration and operator checklist for the current AI Software Factory browser workflow.

---

# Demo Flow

## Step 1 — Browser App Build

Objective:

- Create a browser app-build request.
- Generate DB-preview files.

Expected:

- Workflow run created.
- Generated files persisted.
- No code execution.
- No deployment.

Validation:

- Workflow run visible.
- Generated files visible.

---

## Step 2 — Browser Review & Edit

Objective:

- Open generated files.
- Review content.
- Save edits.

Expected:

- Version history available.
- Changes persisted in DB-preview storage.

Validation:

- Edited content reloads correctly.
- Version history exists.

---

## Step 3 — Approval-Gated Materialization

Objective:

- Approve materialization.
- Materialize static preview files.

Expected:

- Files written only to approved sandbox.

Validation:

- Files exist under workspace.
- No runtime execution.

---

## Step 4 — Static Preview Smoke Test

Objective:

- Verify preview content.

Expected:

- index.html present.
- Linked assets present.

Validation:

- Asset paths detected.
- Assets exist under workspace.

---

## Step 5 — Repair Proposal

Objective:

- Detect preview issues.

Expected:

- Proposal generated.
- No repair applied.

Validation:

- Proposal exists.
- Proposal-only mode confirmed.

---

## Step 6 — Approval-Gated Repair Apply

Objective:

- Explicit approval required.
- Apply approved repair.

Expected:

- Repair blocked before approval.
- Repair succeeds after approval.

Validation:

- Repair target exists.
- Repair remains sandbox-bound.

---

## Step 7 — Re-Test

Objective:

- Re-run validation after repair.

Expected:

- Smoke test passes.

Validation:

- Re-test status = passed.

---

# Operator Checklist

## Pre-Demo

- [ ] Latest main branch pulled.
- [ ] Database available.
- [ ] Browser workspace operational.
- [ ] No pending migrations.
- [ ] No local uncommitted changes.

## During Demo

- [ ] Build request created.
- [ ] Generated files visible.
- [ ] File edit saved.
- [ ] Materialization approved.
- [ ] Static preview inspected.
- [ ] Repair proposal created.
- [ ] Repair approval granted.
- [ ] Repair applied.
- [ ] Re-test passed.

## Safety Checklist

- [ ] No generated code executed.
- [ ] No runtime server started.
- [ ] No preview server started.
- [ ] No external deployment performed.
- [ ] No approval bypass performed.

---

# Known Limitations

- Static preview only.
- No generated application execution.
- No production deployment.
- Repair actions limited to approved preview workflow.

---

# Milestone Coverage

- V88 Complete
- V89 Complete
- V90 Complete
- V91 Complete
- V92 Complete
- V93 Complete
- V94 Documentation & Operator Readiness
