# AFOS-006 Existing Capability Inspection Report

## Scope

AFOS-006 must connect the existing governed founder-prompt-to-production path without creating a second orchestrator, mission store, approval model, coding agent, PR executor, CI system, deployment engine, verification service, API family, or UI shell.

## Existing authorities inspected

- Mission creation, planning, architecture review, engineering handoff, execution evidence, and resumability are already owned by `app.platform.execution.orchestrator` and the existing execution mission evidence store.
- Repository mutation and PR creation are already owned by the approved GitHub Executor.
- PR identity and lifecycle observation are already owned by the existing PR lifecycle service.
- Native Coding Agent and executable change-set generation already produce mission-scoped file changes and validation evidence.
- Founder Workflow, Founder Approval, Executive Decision Center, Board Room, Executive Inbox, and Proactive Jarvis Briefings already own their respective governance and presentation boundaries.
- CI repair, deployment, rollback, traffic movement, and production verification already exist as independent governed capabilities and must remain authoritative.

## Confirmed missing handoff

The existing execution orchestrator currently stops after PR creation and observation. It does not expose one mission-continuation contract that reports the next governed stage across CI, repair, merge, deployment, rollback readiness, and production verification.

AFOS-006 will add only a continuation projection and stage-transition contract over existing evidence. It will not perform a governed mutation unless the matching existing authority and exact approval evidence are supplied.

## State authority and idempotency

- Canonical mission evidence remains the sole durable execution record.
- Existing evidence keys are reused for planning, architecture, handoff, change set, repository execution, PR lifecycle, CI, merge, deployment, rollback readiness, and production verification.
- Repeated continuation requests must return the same current stage when no new authoritative evidence exists.
- Completed stages must be reused rather than repeated.

## Approval boundaries

Separate explicit approvals remain required for:

1. repository mutation and PR creation;
2. merge;
3. production deployment or traffic movement;
4. rollback.

Planning, inspection, status projection, CI observation, and production verification reads remain non-mutating.

## Approved extension points

1. Extend `app.platform.execution.orchestrator` with a mission-continuation function that reads existing evidence and identifies the next governed action.
2. Record only existing-authority outputs as mission evidence.
3. Return a single founder-facing stage contract containing progress, blocker, evidence, recovery action, approval requirement, and completion status.
4. Add deterministic validation for resumability, idempotency, approval separation, failure recovery, and no-duplication governance.

## Architecture decision

Proceed with a thin continuation layer inside the existing execution orchestrator. Do not add a new orchestrator, queue, scheduler, mission store, executor, deployment service, or verification service.
