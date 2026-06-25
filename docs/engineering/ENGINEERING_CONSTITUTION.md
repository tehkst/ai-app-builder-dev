# V98 Engineering Constitution

## Purpose

The AI Software Factory is not a prompt-to-code toy. It is an engineering operating system that must follow the same discipline as real software delivery: scope first, build second, review third, test fourth, repair fifth, approve before rollout.

This constitution defines the non-negotiable rules for all future platform, customer, migration, repair, and self-improvement work.

## Core Principle 1: Scope Before Build

No coding, migration, generated artifact materialization, deployment, or production change may begin until the work has a scoped contract.

A valid scope contract must define:

- business goal
- work type
- requested capabilities
- in-scope items
- out-of-scope items
- acceptance criteria
- affected systems
- risks
- test plan
- approval gate
- rollout target
- rollback expectation

This mirrors a real project lifecycle where customers sign off on project scope before engineering begins.

## Core Principle 2: Every Change Is a Workflow

Every engineering request becomes a workflow.

Minimum lifecycle:

1. Intake
2. Classification
3. Scope Contract
4. Scope Approval
5. Planning
6. Build Preview
7. Review
8. Test
9. Repair if needed
10. Approval
11. Materialization
12. Rollout
13. Production Verification
14. Engineering Memory Record

No agent may bypass this lifecycle.

## Core Principle 3: Capability Driven Work

Workflows do not ask for fixed agents by name. Workflows ask for capabilities.

Examples:

- platform.scope
- platform.validator
- platform.workflow
- platform.registry
- platform.security
- platform.migration
- platform.repair
- platform.documentation
- customer.backend
- customer.frontend
- customer.database
- customer.auth
- customer.integration
- customer.payment
- customer.ai

The registry maps required capabilities to available specialists.

## Core Principle 4: Platform and Customer Work Are Different Divisions

The factory has two primary divisions.

### Platform Division

Responsible for improving the factory itself:

- agents
- registry
- workflow engine
- validation engine
- materialization engine
- approval gates
- self-healing
- migrations
- security
- observability
- engineering memory

### Product Division

Responsible for customer-facing application generation:

- FastAPI modules
- React modules
- SQLAlchemy models
- migrations
- auth
- integrations
- reports
- dashboards
- user workflows

The two divisions share workflow infrastructure but must not share build strategy blindly.

## Core Principle 5: No Materialization Without Approval

Generated artifacts are DB-preview records until explicitly approved.

Forbidden before approval:

- disk write of generated app files
- filesystem mutation
- generated-code execution
- dependency installation
- external deployment
- production database migration
- production configuration mutation

## Core Principle 6: Review and Test Are Mandatory

A generated or changed artifact is not ready until it has passed:

- reviewer checks
- compatibility checks
- test checks
- safety checks
- scope-conformance checks

For customer projects, this is equivalent to SIT/UAT readiness. For platform projects, this is equivalent to internal release readiness.

## Core Principle 7: Bugs and Change Requests Re-enter Scope

A bug fix, change request, or enhancement is not an informal patch. It must re-enter the workflow as a scoped contract.

The contract may be smaller, but it must still define:

- defect or change requested
- expected behavior
- affected components
- tests to prove the fix
- rollout and rollback expectation

## Core Principle 8: Every Workflow Produces Engineering Memory

Every completed workflow must produce a durable engineering record.

Record fields:

- goal
- classification
- scope contract
- capabilities requested
- agents used
- generated artifacts
- review findings
- test results
- repair attempts
- approval decision
- materialization status
- rollout result
- lessons learned

Future workflows must be able to consult this memory before planning similar work.

## Core Principle 9: Safety Beats Speed

The factory should move quickly, but never by weakening scope, review, testing, approval, or rollback boundaries.

## Core Principle 10: The Factory Is Its First Customer

Every new platform capability should first prove that it can safely improve the factory itself before it becomes part of customer application generation.
