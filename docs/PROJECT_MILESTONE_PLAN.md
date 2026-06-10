# AI Software Factory — Project Milestone Plan

Repository: `tehkst/ai-app-builder-dev`

This file is the source of truth for the current development roadmap.

---

## 1. Current Handover Snapshot

Current merged baseline:

`211b4690 Update roadmap to activate V95`

Current completed milestone:

`V94 — Private MVP Demo Script & Operator Checklist`

Current active milestone:

`V95 — SaaS Module Blueprint Generator`

Current project status:

The private MVP browser shell is operational on Railway. V88-V94 are complete. The project is now moving from browser app-build preview/review/repair flow into blueprint-only SaaS module planning.

Current product capability:

```text
Browser app-build request
→ DB-preview generated files
→ Browser file review/edit/versioning
→ Approval-gated static preview materialization
→ Static preview browser smoke inspection
→ Proposal-only self-healing repair planning
→ Approval-gated generated-preview repair apply
→ Read-only re-test
→ Private MVP demo/operator checklist
→ SaaS module blueprint planning

2. Product Direction

Build the minimum self-building and self-healing app factory loop:

Generate
→ Store as DB-preview
→ Review/edit in browser
→ Approve static preview/materialization
→ Inspect preview safely
→ Detect failure
→ Propose repair
→ Approve repair
→ Apply repair
→ Re-test
→ Prepare module blueprint
→ Approve implementation later

The long-term direction is:

Generate
→ Review
→ Preview
→ Test
→ Self-heal
→ Re-test
→ Approve
→ Integrate
→ Validate with sandbox data
→ Roll out safely
3. Operating Rules

Work one milestone at a time.

Do not insert, rename, reorder, or replace milestones without explicit user confirmation.

The user has explicitly approved:

V88-V94 completed roadmap.
V95 activation as the current milestone.
Cleaning and replacing this roadmap document manually through VS Code for this specific case.

Use GitHub direct connection for repository inspection, branch review, file review, PR creation, PR status inspection, and merging when safe.

Use the local Mac workflow when:

GitHub direct update is unreliable.
Local validation is required.
The user explicitly asks to edit with VS Code.
Source-code changes need safer patching and validation.

Do not ask for manual editing unless the user explicitly requests it.

4. Source Code Update Safety Rule

Do not use whole-file overwrite updates for non-trivial source code files through the GitHub contents API when payload truncation or accidental file corruption is possible.

For source code changes, prefer:

GitHub branch plus local patch plus normal git add, commit, and push.
Small targeted edits with local validation.
Git tree/blob patch-style updates where available.
Whole-file overwrite only for short, low-risk files or documentation, after verifying the full file content.

After any source-code change, run syntax or compile validation before continuing.

Documentation files may be replaced manually through VS Code when the user explicitly approves it.

5. Current Safety Boundary

The platform currently supports safe browser-based self-building workflows, but generated code must remain controlled.

Allowed current capabilities:

Browser admin login.
Browser dashboard access.
App-build workflow orchestration.
DB-preview generated-file persistence.
Browser review/edit/save of generated files.
Generated-file version snapshots.
Approval-gated static preview materialization.
Static preview smoke inspection.
Proposal-only repair planning.
Approval-gated generated-preview repair apply.
Read-only re-test after approved repair.
Private MVP demo/operator workflow.
Blueprint-only SaaS module planning during V95.

V95 safety requirements:

blueprint_only = true
module_files_created = false
production_source_mutation_performed = false
database_migration_executed = false
generated_code_execution_performed = false
runtime_server_started = false
preview_server_started = false
external_deployment_performed = false
approval_bypass_performed = false

V95 must not:

Create production module files.
Mutate production source code.
Execute generated code.
Start runtime or preview servers.
Run database migrations.
Deploy externally.
Bypass approval gates.
6. Completed Milestones Summary
Foundation and Runtime Milestones
Milestone	Name	Status
V47	Filesystem Write Guard / Path Guard	Complete
V48	Browser Restore Control Panel	Complete
V49	Browser Workspace File Editor	Complete
V50	Browser App Builder Workspace	Complete
V51	Browser Preview / Run Panel	Complete
V52	Browser Self-Healing Console	Complete
V53	Browser One-Click Repair Flow	Complete
V54	Browser App Build Session Launcher	Complete
V55	Browser App Spec Form / Prompt Builder	Complete
V56	Browser App Build Results Review Panel	Complete
V57	Safe Static Preview Renderer	Complete
V58	Approval-Gated Workspace Materialization Plan	Complete
V59	Materialization Approval Workflow	Complete
V60	Materialization Approval History	Complete
V61	Persistent Approval Record	Complete
V62	Materialization Execution Gate	Complete
V63	Safe Workspace Materialization Dry Run	Complete
V64	Local Sandbox Workspace Writer	Complete
V65	Manual Browser Test Harness	Complete
V66	Browser Manual Test Harness Panel	Complete
V67	Runtime Readiness Detector	Complete
V68	Runtime Run Plan Builder	Complete
V69	Runtime Approval Gate	Complete
V70	First Controlled Sandbox App Run	Complete
V71	Runtime Log Capture	Complete
V72	AI Runtime Failure Analyzer	Complete
V73	Repair Plan Generator	Complete
V74	Repair Approval Gate	Complete
V75	Approval-Gated Repair Executor	Complete
V76	Re-run After Repair	Complete
V77	First Self-Healing Loop	Complete
V78	Self-Build Module Request Flow	Complete
V79	Module Rollout Gate	Complete
V80	Internal Dogfooding Milestone	Complete
V81	Production Config & Healthcheck	Complete
V82	Persistent State Store	Complete
V83	Auth & Admin Access Gate	Complete
V84	Background Job Runner	Complete
V85	Hosted Sandbox Boundary	Complete
V86	Railway/Gcore Deployment Pack	Complete
V87	End-to-End MVP Launch Smoke	Complete
Hosted Browser MVP Milestones
Milestone	Name	Status	Evidence
V88	Real DB-Preview File Generation From Browser App Build	Complete	4d7b0cd
V89	Browser Generated File Review & Edit Flow	Complete	1001eae
V90	Approval-Gated Static Preview Materialization	Complete	b0d40df
V91	Static Preview Browser Smoke Test	Complete	108a2ab
V92	Self-Healing Repair Proposal for Generated Preview Files	Complete	d834167
V93	Approval-Gated Repair Apply & Re-Test Loop	Complete	cf0da48
V94	Private MVP Demo Script & Operator Checklist	Complete	422a3f9
7. V88-V94 Completion Evidence
V88 — Real DB-Preview File Generation From Browser App Build

Status: Complete.

Evidence:

PR #128 merged.
Merge commit: 4d7b0cd V88: Add DB-preview generated file persistence.
Generated file count verified as 4.
Generated files verified:
index.html
styles.css
app.js
README.md
Safety verified:
DB-preview only.
No disk write.
No filesystem write.
No generated-code execution.
No external deployment.
V89 — Browser Generated File Review & Edit Flow

Status: Complete.

Evidence:

PR #129 merged.
Merge commit: 1001eae V89: Add browser generated file review edit flow.
Browser editor loads full DB-preview content.
DB-preview edit/save verified.
Version snapshot creation verified.
Version history verified.
Safety verified:
No disk write.
No generated-code execution.
No static preview materialization during V89.
V90 — Approval-Gated Static Preview Materialization

Status: Complete.

Evidence:

PR #130 merged.
Merge commit: b0d40df V90: Add approval-gated static preview materialization.
Execution gate blocks before approval.
Approval grants static preview materialization capability.
Sandbox writer restricts materialization to static preview file extensions.
Approved static file materialization verified.
Target path verified under guarded workspace sandbox.
Safety verified:
No generated-code execution.
No runtime server.
No preview server.
No external deployment.
No approval bypass.
V91 — Static Preview Browser Smoke Test

Status: Complete.

Evidence:

PR #131 merged.
Merge commit: 108a2ab V91: Add static preview browser smoke test.
Smoke check reads approved materialized index.html.
Linked static assets verified:
styles.css
app.js
Generated app request visibility verified in preview HTML.
Safety verified:
Read/inspect only.
No generated-code execution.
No runtime server.
No preview server.
No external deployment.
No approval bypass.
V92 — Self-Healing Repair Proposal for Generated Preview Files

Status: Complete.

Evidence:

PR #132 merged.
Merge commit: d834167 V92: Add generated preview repair proposal.
Generated preview repair proposal service added.
Smoke check detects missing linked static asset.
Proposal-only repair planning verified.
Safety verified:
No repair apply.
No DB content mutation.
No filesystem write.
No generated-code execution.
No runtime server.
No preview server.
No external deployment.
No approval bypass.
V93 — Approval-Gated Repair Apply & Re-Test Loop

Status: Complete.

Evidence:

PR #133 merged.
Merge commit: cf0da48 V93: Add approval-gated preview repair apply retest.
Repair apply blocked before approval.
Explicit approval required.
Scoped repair apply verified after approval.
Repaired preview target verified under workspace.
Read-only re-test verified.
Safety verified:
No approval bypass.
No generated-code execution.
No runtime server.
No preview server.
No external deployment.
V94 — Private MVP Demo Script & Operator Checklist

Status: Complete.

Evidence:

Main commit: 422a3f9 V94: Add private MVP demo operator checklist.
Documentation added:
docs/PRIVATE_MVP_DEMO_OPERATOR_CHECKLIST.md
Checklist covers:
Private MVP demo flow.
Operator checklist.
Safety checklist.
Known limitations.
Milestone coverage.
Safety verified:
Documentation-only.
No generated-code execution.
No runtime server.
No preview server.
No external deployment.
No approval bypass.
8. Active Milestone
V95 — SaaS Module Blueprint Generator

Status: Active.

Branch:

v95-saas-module-blueprint-generator

Goal:

Generate blueprint-only SaaS module plans from product/module requirements before any implementation work begins.

Input:

A product or module requirement, for example:

Build a school transport route planning module.

Expected output:

Module name.
Module purpose.
User roles.
Role permissions.
Data model draft.
Screens/routes.
API contract draft.
Approval checklist.
Risk notes.
Safety flags.

V95 must produce reviewable planning artifacts only.

V95 must not create actual implementation files for the generated SaaS module.

Suggested implementation files:

app/platform/services/saas_module_blueprint_service.py
app/platform/agents/saas_module_blueprint_check.py

Suggested service output fields:

module_name
module_purpose
roles
permissions
data_model
screens
routes
api_contract
approval_checklist
risk_notes
safety_flags

Required V95 safety flags:

blueprint_only = true
module_files_created = false
production_source_mutation_performed = false
database_migration_executed = false
generated_code_execution_performed = false
runtime_server_started = false
preview_server_started = false
external_deployment_performed = false
approval_bypass_performed = false

V95 success criteria:

A SaaS module blueprint can be generated from a requirement.
The blueprint includes roles, permissions, data model, screens/routes, API contract, approval checklist, and risk notes.
The blueprint output is deterministic enough for smoke testing.
The smoke check verifies V95 is blueprint-only.
The smoke check verifies no module files are created.
The smoke check verifies no production source mutation.
The smoke check verifies no migrations, execution, runtime server, preview server, deployment, or approval bypass.

Suggested validation commands:

python -m py_compile app/platform/services/saas_module_blueprint_service.py app/platform/agents/saas_module_blueprint_check.py

python app/platform/agents/saas_module_blueprint_check.py
9. Tentative Post-V95 Roadmap

These milestones are not active unless the user explicitly activates them.

V96 — Approval-Gated Platform Module Integration

Goal:

Allow approved generated module blueprints to become implementation plans and controlled source-code changes.

Safety direction:

Require explicit approval before implementation.
Preserve rollback and audit trail.
Prevent direct production mutation without approval.
V97 — Module Migration & Data Contract Planner

Goal:

Generate database migration plans and data contract changes before any migration runs.

Safety direction:

Propose schema/data contract changes before implementation.
Validate migration risks.
Require approval before migration materialization.
Protect production data.
V98 — Real Data Sandbox Seeding & Validation

Goal:

Validate generated modules against realistic non-sensitive seeded sandbox data.

Safety direction:

Use non-sensitive data only.
Validate behavior in isolated environment.
Capture failures for repair proposal generation.
Prevent generated modules from accessing production data.
V99 — Production Readiness Gate for Generated Modules

Goal:

Require automated validation, smoke results, repair history, and operator approval before a generated module becomes rollout-eligible.

Safety direction:

Aggregate validation evidence.
Block rollout unless required gates pass.
Keep approval explicit and auditable.
V100 — Approval-Gated Platform Feature Rollout

Goal:

Roll out approved self-generated modules into the product through a controlled, auditable process.

Safety direction:

Roll out only after readiness gates pass.
Maintain rollback and audit records.
Track deployed module version and source generation run.
Preserve production safety and operator control.
10. Deferred Product Work

Deferred until explicitly approved:

Drag-and-drop app builder.
Marketplace, templates, and plugins.
Multi-user team layer beyond minimum admin/private beta access.
Billing and customer onboarding.
External deployment/export connectors.
Advanced workflow builder.
Production rollout of generated modules.
Production database migrations from generated modules.
11. Standard Validation Reminder

Every future milestone or operational change should include:

Syntax check.
Specific smoke check.
Safety-boundary verification.
Secret-exposure check where deployment or environment config is involved.
Function registry check for internal module/function breakage where relevant.
Rendered dashboard JavaScript syntax check with node --check whenever APP_BUILD_DASHBOARD_HTML changes.
12. Next Chat Startup Instructions

When continuing in a new chat, start by verifying the latest branch and this file.

Required commands:

cd /Users/toniteh/Desktop/ai-app-builder-dev
git status
git branch --show-current
git log --oneline -5
grep -n "Current Handover Snapshot\|Current active milestone\|V95 — SaaS Module Blueprint Generator\|Active Milestone" docs/PROJECT_MILESTONE_PLAN.md

If still working on V95, continue from:

V95 — SaaS Module Blueprint Generator

Do not start V96 or later until V95 is complete, merged, and the user explicitly activates the next milestone.

13. Current Stop Point

Current stop point:

V95 branch active.
Roadmap cleaned.
Next step is implementing the V95 blueprint-only service and smoke check.

After replacing it in VS Code, run:

```bash
git status
git add docs/PROJECT_MILESTONE_PLAN.md
git commit -m "Clean up milestone plan for V95"
git push origin v95-saas-module-blueprint-generator

Then paste:

git log --oneline -5
git status