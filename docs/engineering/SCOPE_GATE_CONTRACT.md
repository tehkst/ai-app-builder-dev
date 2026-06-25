# V98 Scope Gate Contract

## Purpose

The scope gate is the formal boundary between request intake and engineering execution. It ensures the factory behaves like a real delivery organization: no coding begins until the work is classified, scoped, risk-assessed, testable, and approved.

## Scope Gate States

```text
DRAFT
  ↓
READY_FOR_SCOPE_APPROVAL
  ↓
SCOPE_APPROVED
  ↓
BUILD_PREVIEW_READY
  ↓
REVIEW_READY
  ↓
TEST_READY
  ↓
REPAIR_REQUIRED or APPROVAL_READY
  ↓
MATERIALIZATION_APPROVED
  ↓
ROLLOUT_READY
  ↓
ROLLED_OUT
```

## Work Types

A scope contract must declare exactly one primary work type:

- `platform_improvement`
- `customer_product`
- `bug_fix`
- `migration`
- `security`
- `performance`
- `documentation`
- `research`
- `operations`

## Required Contract Fields

```json
{
  "scope_contract_id": "scope_contract_<id>",
  "goal": "Human-readable project goal",
  "work_type": "platform_improvement",
  "division": "platform",
  "requested_capabilities": ["platform.validator"],
  "in_scope": [],
  "out_of_scope": [],
  "acceptance_criteria": [],
  "affected_systems": [],
  "risks": [],
  "test_plan": [],
  "approval_required_before_build": true,
  "approval_required_before_materialization": true,
  "rollout_target": "db_preview_only",
  "rollback_plan_required": true
}
```

## Valid Contract Rules

A contract is valid only if:

1. `goal` is not empty.
2. `work_type` is one of the approved work types.
3. `division` is either `platform` or `product`.
4. `requested_capabilities` contains at least one capability.
5. `acceptance_criteria` contains at least one testable item.
6. `test_plan` contains at least one validation step.
7. materialization approval is required for any filesystem, deployment, migration, or production-impacting work.
8. rollout target is explicit.
9. rollback expectation is explicit.
10. out-of-scope items are recorded so change requests can be detected later.

## Division Mapping

| Work Type | Default Division |
|---|---|
| platform_improvement | platform |
| bug_fix | platform or product depending on affected system |
| migration | platform |
| security | platform |
| performance | platform |
| documentation | platform |
| research | platform |
| operations | platform |
| customer_product | product |

## Lifecycle Mapping

### 1. Intake

The user request is captured unchanged.

### 2. Classification

The Engineering Director classifies the request into work type, division, risk level, and required capability families.

### 3. Scope Contract Draft

The scope contract is drafted with in-scope and out-of-scope boundaries.

### 4. Scope Approval

The user or platform admin approves the scope before build work begins.

### 5. Build Preview

Agents generate DB-preview artifacts only.

### 6. Review and Test

Reviewer and tester verify the output against the signed scope.

### 7. Repair

Failed review or failed tests produce scoped repair work.

### 8. Materialization Approval

Materialization requires explicit approval.

### 9. Rollout

Approved work is materialized, committed, deployed, or released according to the rollout target.

### 10. Production Verification

Post-rollout checks confirm expected behavior.

### 11. Engineering Memory

The workflow outcome is recorded for future retrieval.

## Change Request Rule

Any request that changes the approved contract must create either:

- a new scope contract, or
- a revision of the existing contract with explicit approval.

## Bug Fix Rule

A bug is not fixed directly. It becomes a scoped bug-fix contract with reproduction steps, expected behavior, regression tests, and rollout/rollback requirements.
