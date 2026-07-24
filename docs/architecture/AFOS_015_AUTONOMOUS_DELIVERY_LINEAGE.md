# AFOS-015 Autonomous Delivery Lineage

## Purpose

AFOS-015 reconstructs the evidence-backed delivery journey for a governed
mission. It answers what happened, why, which canonical authority acted, which
evidence and artifacts resulted, which governance boundary applied, and what
should happen next.

Contract: `autonomous-delivery-lineage-v1`

## Flow

```text
PlatformWorkflowRun and persisted software-delivery-v1 state
PlatformAgentTask
PlatformOrganizationalEvent authority references
PlatformGovernanceApproval
PlatformExecutionEvidence
PlatformOperationalEvidence
        |
        v
read-only source adapters
        |
        v
normalization -> causal linking -> gap validation -> replay filtering
        |
        +-> Founder Delivery Lineage view
        +-> AKG read-only mission/workflow relationship
```

## Authority

The projection owns no state. Mission Runtime, Workflow Run Persistence,
Platform Agent Worker, Governance Authorization, Native Coding Agent, GitHub,
Cloud Run, Production Verification, and the `software-delivery-v1` contract
remain authoritative.

`PlatformOrganizationalEvent` is reused as an append-only, non-authoritative
reference stream. AFOS-015 does not add an event store, audit log, artifact
registry, mission history, deployment history, tracing database, or migration.

## Causality

Explicit `causation_id`, task identity, workflow identity, artifact source
references, approval identifiers, and release identifiers are used when
available. Chronological proximity alone never establishes causality. Unknown
causality is returned as `unknown`.

## Replay

The same reconstruction supports chronological and causal replay, with bounded
filters for stage, agent, evidence type, failures and repairs, governance, and
repository/deployment activity. Replay is inspection only and never repeats AI
calls or mutations.

## Security

The public contract returns summaries, hashes, and stable references. It does
not return source contents, provider payloads, hidden prompts, chain of thought,
cookies, tokens, credentials, or secret environment values. Known credential
patterns in error summaries and evidence references are redacted at the
serialization boundary.

## Gaps

Evidence completeness is classified as `complete`, `partial`, `unknown`, or
`inconsistent`. The projection reports missing producers, artifacts, merge or
deployment links, provider/model provenance, contradictory timestamps, and
duplicate transitions without silently inventing evidence.

## Cache and Availability

AFOS-015 currently uses no projection cache. Reconstruction reads canonical
records on every request. A future cache may be added only if it remains
non-authoritative, reconstructable, safe to discard, and unnecessary for
workflow correctness.
