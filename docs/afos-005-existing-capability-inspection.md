# AFOS-005 Existing Capability Inspection Report

## Scope

AFOS-005 must make Jarvis proactively brief the Founder using existing authoritative signals. It must not create another scheduler, notification system, inbox, mission registry, persistence model, API family, or UI shell.

## Existing capabilities inspected

### Executive Intelligence

- `app.platform.executive_intelligence.service.build_executive_intelligence_briefing` already composes repository, mission, GitHub, deployment, verification, health, sprint, release, and Board Room evidence.
- It already exposes blockers, risks, next recommended action, source evidence, freshness metadata, and read-only governance.
- This remains the briefing authority and extension point.

### Executive Inbox

- `app.platform.webconsole.executive_inbox_view.executive_inbox_view` already projects approvals, workflows, missions, agent tasks, incidents, pull requests, deployments, and notices into one stateless founder-facing queue.
- It owns no state and routes actions back to source authorities.
- AFOS-005 may summarize these items but must not duplicate their lifecycle or storage.

### Mission, workflow, and approval state

- Mission Pipeline remains the mission authority.
- Workflow runtime inspection and Founder Workflow Engine remain the workflow authorities.
- Founder Approval remains the approval authority.
- Existing agent-task lifecycle events remain the agent assignment authority.

### Board Room and dashboard

- Board Room context and the existing dashboard/navigation remain the founder-facing operating surfaces.
- AFOS-005 will provide a structured briefing payload suitable for those existing surfaces without creating a parallel UI shell.

## Freshness boundaries

- Executive Intelligence evidence is collected on request.
- Source claims must retain checked-at and freshness metadata.
- Missing or stale evidence must be marked explicitly and must not be presented as current fact.
- No background scheduler is introduced by this milestone.

## Duplication review

The following are prohibited and are not introduced:

- new briefing service of record;
- new notification or notice system;
- new autonomous scheduler;
- new inbox or action queue;
- new mission, workflow, approval, or agent-task registry;
- new persistence model;
- new API family;
- new UI shell.

## Approved extension points

1. Extend the existing Executive Intelligence service with a founder-ready proactive briefing projection.
2. Accept existing Executive Inbox source envelopes as optional read-only inputs.
3. Rank priorities, blockers, approvals, mission progress, failed workflows, deployment readiness, risks, and next actions.
4. Preserve evidence references, checked-at values, freshness markers, and source ownership.
5. Add deterministic validation for ranking, de-duplication, stale marking, action routing, and governance.

## Architecture decision

Proceed by extending `app.platform.executive_intelligence` only. Proactive Jarvis Briefings are a stateless projection over existing evidence and inbox signals, not a second source of truth or scheduled automation system.
