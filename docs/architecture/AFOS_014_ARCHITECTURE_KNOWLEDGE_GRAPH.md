# AFOS-014 Architecture Knowledge Graph

## Decision

The Architecture Knowledge Graph (AKG) is the canonical read-only projection of
architecture evidence. It does not own architecture, mission, workflow,
repository, runtime, governance, provider, deployment, or ADR state.

## Capability Audit

| Existing capability | Existing authority | AKG treatment |
|---|---|---|
| Coding Agent dependency analyzer | Python import, symbol, caller, and blast-radius analysis | Reused as the repository import graph adapter; module resolution defect corrected |
| Capability Intelligence | Capability lifecycle, integration, production, authority, and evidence classification | Reused as the authority and lifecycle adapter |
| Repository Intelligence | Safe bounded repository evidence and source fingerprints | Preserved as repository evidence authority |
| Company Graph | Company object relationships | Preserved as the business-object graph; not replaced |
| PMO dependency graph | Story dependencies and critical path | Reused as the workflow projection adapter |
| Agent dependency graph | Agent capability dependencies | Preserved as the agent-domain authority |
| Architecture Agent | Mission-specific architecture decisions and validation | Preserved as the decision-producing authority |
| Company Brain ADRs | Repository-backed architectural rationale | Reused as the ADR projection source |
| Runtime provider router | Provider and model selection | Reused as the provider/runtime source |
| Mission Runtime | Durable mission and workflow state | Preserved as mission state authority |

No pre-existing component provided a cross-domain, typed, evidence-derived
architecture projection. Domain graphs remain supported and feed the AKG.

## Canonical Contract

`architecture-knowledge-graph-v1` contains typed nodes, typed relationships,
evidence references, authority classification, lifecycle, technology, quality,
ownership, operational metadata, health, and a repository revision fingerprint.

The graph is generated lazily and cached for 60 seconds. Cache entries are
invalidated when the repository revision changes or a caller requests an
explicit refresh. The cache is non-authoritative and process-local.

## Projections

- Architecture
- Runtime
- Mission and workflow
- Repository
- Technology and providers
- Governance and ADRs
- Impact analysis

All projections filter the same graph. They do not build parallel models.

## Dead-Code Semantics

`Candidate for Removal` means static inspection found no inbound import,
outbound dependency, or mapped test. It is a review signal, never deletion
authority. Runtime and production evidence can prevent or qualify removal in a
future refinement.

## Consolidation

The former graph implementations are not deleted because they remain canonical
inside their bounded domains. They are deprecated only as candidates for a
cross-platform architecture view. New architecture visualization and impact
features must consume the AKG contract instead of creating another graph.

## Governance

- Read-only projection
- Founder authentication required for detailed evidence and impact requests
- No repository writes
- No runtime, workflow, provider, deployment, or governance mutation
- No automatic deletion or pruning

## Known Limits

- Test coverage percentages are reported as unknown when no current coverage
  evidence exists.
- Production usage is only asserted when existing Capability Intelligence
  provides production evidence.
- Dynamic imports and runtime calls that have no repository or event evidence
  remain unknown.
- Runtime mission nodes are included only when durable mission evidence can be
  inspected without changing state.
