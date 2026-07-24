# ADR-0002: Architecture Knowledge Is a Projection

## Status

Accepted

## Date

2026-07-24

## Context

AI Software Factory already has canonical authorities for repository evidence,
capabilities, missions, workflows, runtime, governance, providers, deployment,
and company decisions. Creating a new architecture registry would duplicate
those authorities and eventually drift from production truth.

## Decision

Architecture Knowledge Graph is a live, read-only projection derived from the
existing authorities. It may cache a repository-revision fingerprint for
performance, but it never owns or mutates source state.

Every node and relationship is typed. Every material conclusion exposes its
evidence. Domain-specific graphs remain authoritative inside their domains and
are adapted into the shared projection.

The canonical contract is `architecture-knowledge-graph-v1`.

## Supersedes

No existing domain graph is superseded. This decision supersedes the use of any
single domain graph as a cross-platform architecture map.

## Consequences

- Architecture views remain aligned with live canonical evidence.
- Impact analysis can cross repository, workflow, runtime, provider, deployment,
  technology, and governance boundaries.
- Dead-code and pruning signals remain recommendations, never deletion actions.
- Missing evidence is reported as unknown instead of fabricated.
- Future architecture visualizations must consume the AKG contract.

## Related implementation

- `app/platform/architecture_knowledge_graph/service.py`
- `app/platform/architecture_knowledge_graph/projection.py`
- `app/platform/coding_agent/dependency_analyzer.py`
- `app/platform/capability_intelligence/service.py`
- `app/platform/repository_intelligence/service.py`
- `app/platform/runtime/provider_router.py`
