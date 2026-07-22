# AFOS-004 Existing Capability Inspection Report

## Scope

AFOS-004 must provide one founder-facing Executive Inbox by aggregating existing actionable items. It must not create a second source of truth.

## Existing capabilities inspected

### Navigation and UI

- The existing admin web console already exposes `/admin/tasks` and `/admin/notices`.
- The existing admin console navigation and `ConsoleView`/`ConsoleCard` models are the UI authority.
- AFOS-004 will extend this shell with an `Executive Inbox` navigation entry and a read-only aggregate view.

### Founder mission actions

- `app.platform.operating_console.action_service.build_pending_mission_actions` already owns founder-facing mission action metadata.
- The existing action service owns action signatures, approval state, mission identifiers, and dispatch targets.
- AFOS-004 must consume its read model and must not copy its action dispatcher or approval logic.

### Workflows and approvals

- The Founder Workflow Engine owns workflow cards, stages, blockers, allowed actions, and approval meaning.
- Founder Approval remains the approval authority.
- AFOS-004 will project workflow and approval items without changing their lifecycle.

### Runtime, missions, and agent tasks

- Mission Pipeline and workflow-run persistence own mission/runtime state.
- Existing agent-task lifecycle events and task records own agent assignments.
- Existing incident, PR orchestration, deployment, and notice capabilities remain their respective authorities.

## Duplication review

The following are prohibited and are not introduced:

- new inbox persistence or inbox database table;
- new task, notice, approval, mission, incident, PR, or deployment registry;
- new action dispatcher;
- new workflow or approval engine;
- new API family;
- new UI shell.

## Approved extension points

1. Extend the existing admin navigation with `/admin/inbox`.
2. Add a read-only projection under `app.platform.webconsole` that accepts existing source envelopes.
3. Normalize actionable items into one founder-facing shape containing priority, source/owner, mission/workflow linkage, required action, status, age, route, and governance boundary.
4. De-duplicate by canonical authority reference while preserving the source system as authority.
5. Add deterministic validation for aggregation, de-duplication, routing, and no-state-ownership guarantees.

## Architecture decision

Proceed by extending the existing admin web console only. Executive Inbox is a stateless projection, not a service of record.