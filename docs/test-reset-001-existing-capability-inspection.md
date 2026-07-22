# TEST-RESET-001 Existing Capability Inspection

## Purpose

Introduce a governed clean-state reset for Jarvis acceptance testing without creating a parallel database, runtime, admin shell, workflow engine, mission store, memory store, or navigation system.

## Existing authoritative capabilities

- Mission and mission evidence remain owned by the existing execution and durable workflow services.
- Jarvis, Board Room, Executive Inbox, deployment evidence, production verification, agent sessions, and memory remain owned by their existing canonical stores.
- The existing admin web console already exposes `/admin/agents` as **Agent Center**.
- The Founder Experience has a separate navigation implementation, explaining why the production sidebar can omit Agent Center even though AFOS-001 is present in the admin console.

## Minimal extension plan

1. Add a reset contract under the existing platform administration boundary.
2. Require preview first, explicit administrative authorization, exact confirmation text, and scope reporting.
3. Delegate clearing to canonical stores through registered reset handlers; no direct cross-domain SQL truncation.
4. Preserve users, authentication, roles, settings, Runtime Constitution, model configuration, installed capabilities, source code, Git history, and deployment configuration.
5. Keep external GitHub and live deployment infrastructure untouched.
6. Add a clean-state verifier that reports remaining operational records and specifically detects `MISSION-44BE9D1DAF0E`.
7. Extend the existing Founder Experience navigation to link to the already-existing Agent Center route rather than creating another agent page.

## Governance boundaries

- Preview is read-only.
- Execution requires administrative authorization and exact confirmation.
- Reset handlers must be explicit and canonical; unsupported domains are reported rather than silently skipped.
- Partial failures are surfaced with per-scope evidence.
- Repeated execution is safe and reports zero additional records when already clean.
- Production reset remains a separate founder action after deployment; this implementation does not reset production data during merge or deployment.

## Duplication risks avoided

- No second mission store.
- No second memory service.
- No second admin UI.
- No direct database-wide purge utility.
- No new scheduler or orchestration engine.
- No synthetic deployment or GitHub history deletion.
