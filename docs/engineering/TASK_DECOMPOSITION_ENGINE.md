# V99 Task Decomposition Engine

## Purpose

V99 changes the Builder from a direct code generator into an Engineering Project Manager that produces a task graph.

The factory should not ask one Builder Agent to design backend, frontend, database, tests, documentation, rollout, and repair by itself. A real engineering organization decomposes the approved scope into many smaller tasks, assigns them to specialists, tracks dependencies, reviews work, tests outputs, and repairs failures.

## Core Shift

Before V99:

```text
Scope Approved
  -> Architect
  -> Builder
  -> Reviewer
  -> Tester
```

After V99:

```text
Scope Approved
  -> Architect
  -> Task Decomposition Engine
  -> Engineering Task Graph
  -> Specialist Teams
  -> Review
  -> Test
  -> Repair
  -> Approval
```

## Task Graph Principles

A valid task graph must define:

- graph id
- source scope contract id
- engineering division
- work type
- tasks
- dependencies
- required capabilities
- expected outputs
- acceptance criteria
- review gate
- test gate
- materialization gate

## Task Types

Approved engineering task types:

- `architecture`
- `backend`
- `frontend`
- `database`
- `migration`
- `validation`
- `testing`
- `security_review`
- `documentation`
- `release`
- `repair`
- `platform_engineering`

## Capability Examples

Product division capabilities:

- `customer.backend`
- `customer.frontend`
- `customer.database`
- `customer.auth`
- `customer.testing`
- `customer.documentation`

Platform division capabilities:

- `platform.builder`
- `platform.validator`
- `platform.workflow`
- `platform.registry`
- `platform.testing`
- `platform.documentation`
- `platform.security`
- `platform.repair`

## Minimum Product App Task Graph

For a customer product request, the minimum task graph should include:

1. architecture task
2. backend contract task
3. data model task
4. frontend shell task
5. test contract task
6. review task
7. release readiness task

## Minimum Platform Improvement Task Graph

For a platform improvement request, the minimum task graph should include:

1. scope and design task
2. platform implementation task
3. compatibility validation task
4. regression test task
5. documentation task
6. review task
7. rollout readiness task

## Safety Rules

The task graph does not materialize code.

The graph only defines work to be performed after scope approval. Specialist execution still must obey:

- DB-preview first
- no filesystem materialization before approval
- no generated-code execution before approval
- no dependency installation before approval
- no deployment before approval
- repair loop before rollout

## Future Direction

V99.1 should connect the generated task graph into workflow execution so the existing fixed four-step workflow can be replaced by dynamic task graphs.
