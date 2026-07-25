---
mission_id: AFOS-017A
title: Integrated AI Organisation Console
branch: codex/afos-017a-organisation-console
status: engineering-complete-release-pending
started_at: 2026-07-25
engineering_completed_at: 2026-07-26
base_commit: 9b6d849476d2c98e2278e31bd759f0b62a5bcd78
delivery_lineage_contract: autonomous-delivery-lineage-v1
delivery_lineage_runtime_link: pending-durable-mission-run
architecture_contract: architecture-knowledge-graph-v1
architecture_evidence:
  - docs/architecture/afos-017a-implementation-map.md
  - app/platform/organization_console/
---

# AFOS-017A Mission Completion Report

## Mission Metadata

| Field | Value |
|---|---|
| Mission ID | `AFOS-017A` |
| Title | Integrated AI Organisation Console |
| Branch | `codex/afos-017a-organisation-console` |
| Started | 25 July 2026 |
| Engineering completed | 26 July 2026 |
| Status | Engineering complete; commit, review, merge, deployment, and production acceptance pending |
| Base revision | `9b6d849476d2c98e2278e31bd759f0b62a5bcd78` |
| Runtime mission ID | Not created for this engineering branch |
| Workflow run ID | Not created for this engineering branch |

This report remains under `company/missions/active` until release and production
acceptance are complete. It should move to `company/missions/completed` only
after the merged revision and production verification evidence are recorded.

## Scope Delivered

- Added a founder-facing Organisation Console as the canonical view of AI
  departments, teams, workers, reporting relationships, capabilities, workload,
  skills, and durable contribution evidence.
- Added organisation chart and directory views with search, filters,
  pagination, expand/collapse, pan, zoom, fit, reset, responsive fallback, and
  accessible navigation.
- Added department, team, and worker profiles.
- Added deferred worker evidence views for current jobs, mission history,
  activity, Delivery Lineage, Architecture Knowledge Graph, repository
  contributions, deployments, and production verification.
- Added repository-backed operational `skills.md` documents for the registered
  specialist workforce.
- Added runtime skill injection and diagnostics without granting execution
  authority.
- Added governed skill change preview, history, version inspection, and restore
  preparation through existing GitHub execution governance.
- Replaced synthetic legacy Workforce records with a compatibility adapter over
  the canonical Organisation projection.
- Preserved the legacy `#agents` URL as an alias to `#organisation`.
- Added bounded caching, directory windowing, evidence pagination, focused
  validation, and performance checks.

## Existing Capabilities Reused

| Capability | Reuse |
|---|---|
| Agent Registry | Canonical worker identity and executable agent handlers |
| Agent Manifest Registry | Capabilities, dependencies, inputs, outputs, and approval boundaries |
| Organisation Registry | Canonical department and team structure |
| Management Registry | Existing management roles and reporting metadata |
| Mission Runtime | Durable workflow and mission context |
| `PlatformAgentTask` | Current work, workload, assignments, and worker status |
| Workflow Run Persistence | Mission/workflow identity and stage evidence |
| Delivery Lineage | Read-only worker contribution and mission history projection |
| Architecture Knowledge Graph | Read-only architecture contribution and dependency evidence |
| Execution and Operational Evidence | Repository, deployment, verification, and runtime evidence |
| Governance Authorization | Authority for consequential actions; capability remains separate |
| Founder Authentication | Access boundary for all Organisation detail endpoints |
| GitHub Execution | Governed skill change preview and pull-request path |
| Stable Founder Dashboard | Existing shell, navigation, visual tokens, and routing |

No new database, mission store, worker registry, event stream, governance
authority, deployment authority, or architecture graph was created.

## Components Modified

### Runtime and authority integration

- `app/platform/agents/worker.py`
- `app/platform/organization/registry.py`
- `app/platform/memory/registry.py`
- `app/platform/board_room/context_retriever.py`
- `app/platform/server.py`

### Canonical Organisation projection

- `app/platform/organization_console/service.py`
- `app/platform/organization_console/evidence.py`
- `app/platform/organization_console/skills.py`
- `app/platform/organization_console/__init__.py`

### Founder experience

- `app/platform/ui/organisation_console_script.py`
- `app/platform/ui/founder_dashboard_stable.py`
- `app/platform/ui/dashboard_browser_script.py`
- `app/platform/ui/nav_model.py`

### Compatibility and validation

- `app/platform/ai_workforce/service.py`
- `app/platform/organization_console/check.py`
- `app/platform/organization_console/evidence_check.py`
- `app/platform/organization_console/performance_check.py`
- `app/platform/ui/check.py`
- `app/platform/agents/skills/*/skills.md`

The detailed authority and integration map is
[AFOS-017A Implementation Map](../../../../docs/architecture/afos-017a-implementation-map.md).

## Components Deprecated or Adapted

| Component | Treatment |
|---|---|
| Static Agents dashboard section | Removed as a presentation source because it was not authoritative |
| `#agents` route | Retained as a compatibility alias to `#organisation` |
| Legacy Workforce API | Retained as a compatibility adapter over the Organisation projection |
| Synthetic workforce records | Removed from the compatibility response |
| Existing domain registries | Preserved as canonical authorities; not duplicated |

## Validation Results

### Complete validation pipeline

`python3 -m app.platform.validate_all` passed its complete local profile,
including compatibility, dependency policy, platform routes, agent manifests,
organisation hierarchy, memory, knowledge graph, management, runtime,
governance, authentication, Executive Intelligence, conversation contracts,
delivery, AKG, Delivery Lineage, SaaS factory, deployment foundations, and
provider-independent checks.

### Focused release validation

| Validation | Result |
|---|---|
| `python3 -m compileall app` | Passed |
| Organisation Console contract | Passed |
| Organisation evidence integration | Passed |
| Organisation performance | Passed |
| Runtime reconciliation | Passed |
| Mission Execution UI lifecycle | Passed with isolated persistence |
| Mission identity through merge | Passed with isolated persistence |
| Action progress UI | Passed |
| Journey Inspector | Passed |
| Delivery Lineage | Passed |
| Architecture Knowledge Graph | Passed |
| Worker lease renewal and owner fencing | Passed |
| Login and UI module boundaries | Passed |
| Python 3.9 compatibility | Passed |
| Dashboard rendering | Passed |
| Generated dashboard JavaScript `node --check` | Passed |
| `git diff --check` | Passed |

One parallel validation attempt produced a SQLite `StaleDataError` because two
persistence-heavy checks shared the same local database. The affected Mission
Execution check passed when rerun alone against an isolated database. This was
test orchestration contention, not a runtime regression.

## Browser Acceptance Evidence

Browser acceptance was completed against the local AFOS-017A application using
founder authentication.

Verified journeys:

- Organisation chart and directory.
- Department and team expansion and detail.
- Worker profile and operating scope.
- Skills source, runtime diagnostics, editor, and lifecycle wording.
- Current jobs and mission history.
- Delivery Lineage, AKG, repository, deployment, verification, and activity
  evidence tabs.
- Organisation-to-Architecture, Lineage, and Deployments navigation.
- Expand/collapse, zoom, fit, reset, keyboard panning, directory search, and
  responsive rendering.
- Honest empty states when no authoritative worker evidence was available.
- No local browser console errors.

Evidence:

- [Organisation chart](evidence/organisation-chart.jpg)
- [Worker skills and runtime diagnostics](evidence/worker-skills.jpg)
- [Desktop responsive acceptance](evidence/desktop-responsive.jpg)
- [Mobile responsive acceptance](evidence/mobile-responsive.jpg)

## Performance Measurements

Measured locally with the focused performance check:

| Measurement | Result |
|---|---:|
| Cold Organisation landing projection | 97.87 ms |
| Cached Organisation landing projection | 0.30 ms |
| Worker profile | 8.65 ms |
| Worker evidence projection with 500 tasks | 257.06 ms |
| Directory render window | 100 workers |
| Default evidence page | 25 records |

The 500-task evidence projection remained below the 500 ms acceptance budget.
The five-second process-local cache is non-authoritative and can be discarded
without losing runtime truth.

## Known Baseline Debt

The following checks fail unchanged on the clean base revision and are not
caused by AFOS-017A:

- `app.platform.board_room.natural_conversation_check`
- `app.platform.operating_console.action_flow_check`

Both failures arise from the existing Board Room classifier returning
`product_discovery` for the established production request where the older
checks expect mission-preparation actions.

## Known Limitations

- Two registered workers have no authoritative department assignment and are
  shown as `Unassigned`.
- Local acceptance data contained no worker-linked mission, lineage,
  architecture, repository, or deployment records for the inspected worker.
  The UI reports these as unavailable rather than fabricating history.
- A repository skill version is not described as released or active unless
  runtime load evidence exists.
- Runtime skill-load diagnostics are process-local. Cross-instance activation
  remains dependent on merge, release, and production verification.
- Repository skill history depends on the availability of existing Git history.
- AFOS-017A does not yet have a durable `MISSION-*`/`MISSION-RUN-*` pair, so the
  Delivery Lineage UI cannot resolve this engineering branch as a runtime
  mission until the canonical mission lifecycle records it.

## Technical Debt

- Establish a common isolated persistence fixture for checks that currently
  default to `platform.db`, preventing cross-check SQLite contention.
- Reconcile the two unassigned workers when an authoritative organisation
  decision exists; do not infer assignments in the projection.
- Repair the pre-existing Board Room classification/check mismatch separately
  from AFOS-017A.
- Record the merged commit, pull request, deployment revision, and production
  verification evidence after release.

## Lessons Learned

- Existing registries were individually authoritative but needed a read-only
  projection to become useful to the Founder.
- Stable worker identity must remain separate from transient runtime status and
  historical contribution evidence.
- Repository availability, release, and runtime activation are distinct states;
  founder-facing language must preserve that distinction.
- DOM width metrics alone are insufficient responsive evidence. Viewport
  screenshots exposed capture and layout behavior that required visual review.
- Empty evidence is useful when it is explicit. Fabricated progress or inferred
  contribution history would make the Organisation Console less trustworthy.
- Compatibility routes are safer when they adapt canonical projections instead
  of preserving synthetic parallel records.

## Follow-up Recommendations

1. Authenticate GitHub, commit the validated branch, and open a focused review.
2. Record the PR number and merged commit in this report.
3. Deploy through the existing governed release path and run production
   acceptance for Organisation, worker evidence, and skill runtime semantics.
4. Record the production revision and verification evidence, then move this
   report from `active` to `completed`.
5. Once a canonical durable mission run exists, inspect it through
   [Delivery Lineage](../../../../docs/architecture/AFOS_015_AUTONOMOUS_DELIVERY_LINEAGE.md)
   and confirm the `mission:AFOS-017A` relationship in the
   [Architecture Knowledge Graph](../../../../docs/architecture/AFOS_014_ARCHITECTURE_KNOWLEDGE_GRAPH.md).
6. Address baseline Board Room classification debt in a separate mission.

## Evidence Linkage

| Evidence system | Linkage |
|---|---|
| Mission authority | This report under `company/missions/active/afos-017a` |
| Delivery Lineage | Contract `autonomous-delivery-lineage-v1`; runtime linkage pending a canonical durable mission run |
| Architecture Knowledge Graph | Contract `architecture-knowledge-graph-v1`; repository evidence includes this report, the implementation map, and Organisation modules |
| Implementation architecture | `docs/architecture/afos-017a-implementation-map.md` |
| Browser evidence | `company/missions/active/afos-017a/evidence/` |

This report is documentation and evidence only. It does not mutate runtime,
Lineage, AKG, mission, governance, GitHub, or deployment state.
