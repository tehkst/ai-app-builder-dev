# AFOS-013 Canonical Delivery Architecture

## Decision

AFOS-013 extends the existing durable Board Room mission runtime. It does not
introduce another orchestrator, registry, queue, state machine, or persistence
model.

The canonical chain is:

```text
Founder decision document (PlatformContextStore)
  -> signed mission proposal and Founder Approval
  -> mission state embedded in PlatformWorkflowRun
  -> stage work represented by PlatformAgentTask
  -> existing Planning service
  -> existing Architecture Agent
  -> existing Engineering Manager
  -> existing Native Coding Agent
  -> existing governed GitHub executor
  -> existing PR lifecycle and CI evidence
  -> existing approved merge authority
  -> existing approved Cloud Run authority
  -> existing Production Verification service
  -> founder acceptance embedded in PlatformWorkflowRun
```

`PlatformWorkflowRun` owns mission delivery state. `PlatformAgentTask` owns
leased executable work. Every other component owns only its domain result and
returns evidence to the workflow.

## Canonical State Transition Ownership

| Boundary | Owner | Input contract | Output contract | Persisted record | Idempotency | Approval | Retry / failure | Evidence | Consumer |
|---|---|---|---|---|---|---|---|---|---|
| Conversation to decision | Founder Decision service | Founder conversation response | `founder-decision-v1` | Existing `PlatformContextStore` | action ID plus optimistic version | Material founder decision only | Preserve prior version on conflict/failure | selection events | Mission proposal |
| Decision to mission proposal | Board Room action service | Decision references and recommendation | Signed mission action context | Existing operational evidence/context | Deterministic context signature | Founder mission approval | Invalid/stale signatures block | proposal and signature | Mission acceptance |
| Mission acceptance | `mission_run_service` | Signed context, approval, token | Mission lifecycle envelope | `PlatformWorkflowRun` state step | Deterministic workflow run ID and recheck | Founder approval | Block before side effects if persistence unavailable | accepted step | Agent Worker |
| Stage dispatch | Canonical Agent Worker | `PlatformAgentTask` | Task result/failure | `PlatformAgentTask` | Deterministic task ID per run/stage | None for autonomous stage | Lease, heartbeat, owner fencing, bounded attempts | task lifecycle | Workflow reducer |
| Product definition | Existing Planning service with delivery projection | Accepted decisions, founder objective | Versioned Product Definition artifact | Workflow state artifact index | artifact type/version/source digest | Founder only for material unresolved choices | Regenerate new version; retain prior artifact | validation and decision references | UX and architecture |
| UX specification | Existing product/UI intelligence through workflow stage | Approved Product Definition | Versioned UX Specification artifact | Workflow state artifact index | deterministic artifact key/version | Founder only for material product choice | Block or revise on missing product definition | UX artifact | Architecture and engineering |
| Architecture | Existing Architecture Agent | Approved product/UX artifacts, repository/capability evidence | Validated Architecture artifact | Workflow state artifact index | mission/type/source digest | No routine founder approval | One bounded regeneration; validation failure blocks | architecture validation | Engineering Manager |
| Engineering breakdown | Existing Engineering Manager | Product, UX, architecture references | Engineering Plan artifact | Workflow state artifact index | mission/type/source digest | No routine founder approval | Retry bounded; contradiction blocks | acceptance/validation plan | Native Coding Agent |
| Implementation | Existing Native Coding Agent | Approved engineering plan and workspace/repository binding | VerifiedDiff/change-set evidence | Agent task result plus workflow artifact reference | mission/stage/task ID | Existing scoped implementation/repository policy | Bounded edit/test/repair and non-convergence stop | commands, diff, validation | GitHub executor |
| Repository and PR | Existing governed GitHub executor | Verified file changes and scoped authorization | Branch, commit, PR | GitHub plus workflow evidence reference | branch/mission metadata and existing operation checks | Exact repository mutation approval | Partial operation reported; no direct main | commit/PR metadata | PR lifecycle |
| PR and CI | Existing PR lifecycle | PR identity and mission metadata | Checks and review evidence | GitHub plus workflow evidence | Read-only refresh | None | Unknown external failure is retained | check runs | Repair or merge |
| CI repair | Existing Native Coding Agent repair loop | Failed check evidence and approved scope | Updated VerifiedDiff/commit evidence | Same task/run and PR | bounded repair attempt ID | None if inside approved scope | Retry limit; unrecoverable blocker | failure and repair evidence | PR lifecycle |
| Merge | Existing approved merge authority | PR identity and exact scoped approval | Merge SHA | GitHub plus workflow evidence | already-merged detection | Exact merge approval | Closed/unmergeable/failing checks block | merge result | Deployment preparation |
| Deployment | Existing approved Cloud Run authority | Release/deployment artifact and exact approval | Revision and URL | Cloud Run plus workflow evidence | deployment operation evidence and revision identity | Exact deployment approval | Failure leaves previous revision available | deploy result | Verification |
| Verification | Existing Production Verification service | Service/revision/release identity | Verification report | `PlatformOperationalEvidence` plus workflow reference | evidence ID/source digest | Read-only | Unknown/failed check blocks completion | health/readiness/routes/logs | Founder acceptance |
| Founder acceptance | Existing workflow reducer with new acceptance transition | Verification reference and founder choice | Acceptance artifact/state | `PlatformWorkflowRun` state | action ID and workflow version | Founder decision | Duplicate returns same result; fix/rollback/defer do not complete | acceptance record | Completion/repair/rollback |

## `software-delivery-v1`

The contract is stored in the existing mission state inside
`PlatformWorkflowRun`. Large domain results remain in their existing
authorities; the contract stores compact references and lifecycle summaries.

Required fields:

```text
contract
project_identity
mission_identity
workflow_run_identity
founder_objective
accepted_decision_references
confirmed_assumption_references
unresolved_assumptions
product_definition_reference
target_user
business_outcome
success_criteria
scope
excluded_scope
functional_requirement_references
non_functional_requirement_references
ux_specification_reference
architecture_decision_references
repository_identity
deployment_target
approval_state
current_stage
completed_stages
blockers
next_governed_action
produced_artifact_references
validation_evidence_references
release_evidence_references
production_verification_reference
founder_acceptance_reference
rollback_readiness
created_at
updated_at
version
```

References use stable artifact IDs, workflow IDs, evidence IDs, PR numbers,
commit SHAs, and revision names. Tokens, full prompts, and secret values are
never stored.

## Delivery Artifact Contract

Artifacts are compact versioned records embedded in the existing workflow
state until an existing durable artifact authority is proven suitable for all
required semantics. This does not add a table or registry.

Each artifact contains:

```text
artifact_id
artifact_type
contract
version
status
authoring_authority
mission_id
workflow_run_id
created_at
updated_at
supersedes
approval_state
source_references
evidence_references
content
```

Artifact IDs are deterministic from workflow, type, version, and source
digest. New revisions supersede rather than overwrite approved evidence.

## Stage Model

The durable worker advances only through allowed stages:

```text
accepted
product_definition
ux_specification
architecture
engineering_plan
implementation
repository_approval
pull_request
ci_validation
merge_approval
deployment_approval
production_verification
founder_acceptance
complete
```

Autonomous stages may enqueue their deterministic successor. Governed stages
stop and return the exact existing authority/action required. Stage and retry
limits remain enforced by `PlatformAgentTask`.

## Approval Boundaries

- **Autonomous:** artifact drafting, architecture analysis, engineering
  breakdown, validation, and bounded repair within approved scope.
- **Founder decision:** material product/scope changes and release acceptance.
- **Governed execution:** repository mutation, merge, deployment, traffic
  movement, rollback, and sensitive-system access.

An approval authorizes one action, mission, resource, and bounded scope. A
general conversational instruction does not authorize later governed actions.

## Failure and Recovery

| Failure | Persisted behavior | Resume behavior |
|---|---|---|
| Browser refresh | No state change | Reload workflow and active decision |
| Cloud Run/worker restart | Workflow/task rows remain | Worker reclaims eligible task after lease expiry |
| Duplicate approval/callback | Deterministic action ID returns existing transition | No duplicate task or external mutation |
| Provider timeout | Retryable task failure with bounded attempt | Retry same stage/task identity |
| Invalid artifact | Validation evidence and blocker retained | Regenerate one new version or request material decision |
| CI failure | Check evidence and classification retained | Existing repair loop updates same PR |
| Partial GitHub operation | External identifiers retained | Inspect before retry; never recreate blindly |
| Deployment failure | Failure and previous revision retained | Retry or request rollback approval |
| Verification failure | Release remains unaccepted | Request fix, rollback, or defer |
| Stale workflow version | Reject transition with current version | Client refreshes canonical state |

Founder credentials remain process-local and are never persisted. A sensitive
stage that resumes after restart stops at `authorization_resume_required`
until the founder session is restored.

## Projections, Not Authorities

The following remain read models:

- Mission Pipeline
- Founder Workflow cards
- Executive Brief
- Mission Execution UI
- AFOS-006 continuation projection
- Journey Inspector
- Company Brain and Executive Intelligence summaries

They may recommend or render actions but cannot advance canonical state.

## Deprecation Direction

`app.platform.execution.service._ACTIVE_MISSION` is legacy process-local state.
AFOS-013 must remove the durable worker's dependency on it. Compatibility
entry points may remain temporarily for older callers, but canonical mission
evidence and stage transitions must read and write `PlatformWorkflowRun`.

