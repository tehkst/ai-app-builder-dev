# AFOS-015 Existing Capability and Duplication Audit

## Decision

AFOS-015 is a read-only projection. It does not own mission, workflow, task,
artifact, approval, repository, deployment, verification, or acceptance state.
The existing organizational event store is retained as a non-authoritative,
append-only reference stream and is not replaced by a lineage event store.

## Authority Map

| Capability | Current canonical authority | Existing durable record | Existing API/UI | AFOS-015 action |
|---|---|---|---|---|
| Mission identity | Durable Board Room Mission Runtime | `PlatformWorkflowRun.metadata_json` and persisted handler state | Mission Execution, Mission Pipeline | Reuse |
| Workflow history | Workflow Run Persistence Service | `PlatformWorkflowRun`, `PlatformWorkflowStepRun` | Workflow Pipeline and Mission Execution | Reuse |
| Agent tasks | Platform Agent Worker | `PlatformAgentTask` | Agent Center and runtime projections | Reuse |
| Mission/workflow events | Platform Events boundary | `PlatformOrganizationalEvent` | Company Brain projections | Reuse as non-authoritative evidence |
| Artifacts | `software-delivery-v1` delivery contract and execution workspace | Workflow handler state; `PlatformWorkspaceArtifact` | Mission Execution | Reuse and adapt |
| Decisions and approvals | Governance Authorization and Founder Approval | `PlatformGovernanceApproval`, `PlatformApprovalRequest`, signed action context references | Founder decision and governance surfaces | Reuse |
| Code change evidence | Native Coding Agent and delivery contract | Change-set artifact in workflow handler state; workspace artifacts | Mission Execution engineering view | Reuse |
| Validation and repair | Native Coding Agent validation/repair pipeline | Change-set validation evidence and task result payloads | Mission Execution | Reuse |
| GitHub execution | Governance Authorization plus GitHub API | `PlatformExecutionEvidence`; GitHub branch, commit, PR, and check identifiers | GitHub Execution and PR Lifecycle | Reuse; GitHub remains authoritative |
| Deployment | Approved Cloud Run deployment authority | `PlatformExecutionEvidence` and `PlatformOperationalEvidence` | Deployment panel | Reuse; Cloud Run remains authoritative |
| Production verification | Production Verification service | `PlatformOperationalEvidence`; delivery contract reference | Verification panel | Reuse |
| Founder acceptance | Delivery contract | Persisted workflow handler state | Mission Execution acceptance controls | Reuse |
| Provider and model | Canonical runtime provider router and mission context | Persisted workflow mission context and task payloads | Settings and Mission Execution | Reuse |
| AKG projection | Architecture Knowledge Graph | Reconstructable revision-scoped projection | Architecture view | Integrate through adapter |

## Overlap Decisions

| Existing implementation | Decision | Reason |
|---|---|---|
| `PlatformOrganizationalEvent` | Retain as canonical non-authoritative event reference | Already durable, replay-safe, correlated, causal, and linked to authority references. |
| Mission Pipeline timeline | Convert conceptually to a bounded presentation consumer | It is a derived mission story, not durable lineage authority. |
| Journey Inspector | Retain as capability/integration diagnosis | It answers journey readiness, not record-level delivery lineage. |
| Process-local `execution.service._ACTIVE_MISSION` | Legacy but still referenced; exclude as authority | It is explicitly non-durable and cannot prove production lineage. |
| `PlatformAuditEvent` | Retain for security/route audit | It lacks mission-level causal and artifact semantics. |
| `PlatformExecutionEvidence` | Retain as canonical governed-action evidence | It records authorization, outcome, and release identifiers. |
| `PlatformOperationalEvidence` | Retain as canonical observed production evidence | It records deployment and verification observations. |
| Delivery-contract artifact list | Retain as canonical mission artifact authority | It preserves producer, sources, hashes/identities, supersession, validation, and acceptance references. |
| AKG domain projections | Retain and extend through a read-only lineage adapter | AKG remains architecture authority and does not read execution internals directly. |

## Historical Evidence

The current design follows the durable foundations introduced before AFOS-015:

- `MC-KNOW-02/03`: durable organizational events and authority references.
- `MC-RUNTIME-01A/01C/01D`: durable workflow runs and agent tasks.
- `Sprint 4`: governance authorization and durable execution evidence.
- `AFOS-013`: canonical `software-delivery-v1` contract and governed release lifecycle.
- `AFOS-014`: read-only projection pattern and Atlas/AKG evidence contract.

No migration or new persistence table is required. Lineage reconstruction must
continue to work if its process-local cache is cleared or the application
restarts.
