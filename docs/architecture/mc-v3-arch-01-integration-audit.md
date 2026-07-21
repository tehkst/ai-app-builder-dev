# MC-V3-ARCH-01 — AI Software Factory V3 Integration Audit

Status: execution baseline

## Objective

Transform the existing platform capabilities into one governed Jarvis operating loop without creating parallel memory, reasoning, mission, capability, event, or execution subsystems.

## Constitutional rule

Extend and connect existing capabilities before creating new components.

A new component is permitted only when repository evidence demonstrates that reuse, extension, and integration are insufficient.

## Audited capability map

### Founder interaction and conversation

- Canonical founder interface: Jarvis / Board Room
- Current implementation areas:
  - `app/platform/ui/founder_dashboard_board_chat.py`
  - `app/platform/operating_console/`
- Existing lifecycle support:
  - active, draft, and archived conversation UI states
  - browser refresh restoration
  - New Chat lifecycle
  - governed action cards
- Authority boundary:
  - conversation state is not mission truth
  - browser state is not platform authority

### Executive context

- Canonical owner: Executive Context
- Current implementation areas:
  - `app/platform/persistence/model_definitions/executive_context_store.py`
  - `app/platform/services/executive_context_service.py`
  - `app/platform/api/context_api.py`
- Existing capabilities:
  - SQL-backed persistent context
  - context listing and formatted context blocks
  - conversation summarization
  - Board Room context projection
- V3 role:
  - persistent founder and executive context
  - source for approved principles and bounded conversation summaries
- Must not become:
  - an event store
  - mission state
  - operational evidence

### Executive reasoning and decisioning

- Canonical owners:
  - Executive Reasoning Engine for request orchestration
  - Executive Decision Engine for decision analysis
  - Executive Intelligence for canonical executive read state
- Existing capabilities:
  - dominant-goal and lifecycle decomposition
  - intent fidelity and negative constraints
  - adaptive decision modes
  - evidence, inference, uncertainty, risk, and confidence handling
  - live repository, GitHub, release, deployment, verification, and mission evidence
- V3 role:
  - one executive reasoning pipeline
- Required correction:
  - make capability selection, constitutional checks, approved principles, business impact, and mission evidence explicit stages of one pipeline

### Capability Intelligence

- Canonical owner: `app/platform/capability_intelligence/`
- Existing capabilities:
  - evidence-derived capability read model
  - distributed-source aggregation
  - bounded CAPCTX context
  - overlap and integration signals
  - production-evidence awareness
- Authority boundary:
  - witness only
  - does not make architecture decisions
- V3 role:
  - source of truth for what the platform appears to own
  - input to architecture and executive reasoning
- Required extension:
  - usage evidence
  - overlap candidates
  - obsolete or orphaned capability signals
  - consolidation proposals

### Architecture governance

- Canonical owner: platform-aware Architecture Agent plus Architecture Validator
- Existing decisions:
  - REUSE
  - EXTEND
  - INTEGRATE
  - NEW_COMPONENT_REQUIRED
  - DEPRECATE
  - RETIRE_AFTER_MIGRATION
- Existing governance:
  - new components require evidence that reuse, extension, and integration were evaluated
  - invalid architecture artifacts are blocked
- V3 role:
  - enforce architectural governance before engineering generation
- Required extension:
  - consume approved executive principles
  - consume business impact assessment
  - emit consolidation and retirement evidence

### Mission runtime

- Canonical owners:
  - `PlatformWorkflowRun` for durable mission runtime state
  - `PlatformAgentTask` for worker execution
- Current implementation areas:
  - `app/platform/operating_console/mission_run_service.py`
  - platform persistence and worker runtime
- Existing capabilities:
  - deterministic mission and workflow identities
  - durable task execution
  - retry and continuation
  - governance and founder authorization
  - mission lifecycle projection
- Authority boundary:
  - no Company Brain, browser, chat, or executive projection may own mission truth
- V3 role:
  - canonical source for mission lifecycle events and completed-mission evidence

### Journey Inspector

- Canonical owner: `app/platform/journey_inspection/`
- Existing capabilities:
  - read-only 14-stage mission journey
  - transition verification
  - first broken or manual handoff detection
  - capability-only versus mission-specific evidence separation
- V3 role:
  - evidence source for mission reflection
  - verification of whether the intended operating loop actually completed
- Required extension:
  - normalized reflection evidence contract
  - explicit completed, blocked, failed, and partially verified outcome summaries

### Operational evidence and validation

- Canonical owners:
  - Executive Intelligence evidence registry
  - operational evidence persistence
  - Platform Validation Framework
- Existing capabilities:
  - source status and freshness
  - durable production verification and release snapshots
  - PASS, FAIL, UNKNOWN, and trust-prerequisite semantics
  - founder-authorized live validation
- V3 role:
  - evidence base for reflection and principle promotion
- Authority boundary:
  - reflections cannot override live evidence

### Coding and repository execution

- Canonical owner: Native Coding Agent for coding orchestration
- Existing implementation area:
  - `app/platform/coding_agent/`
- Existing capabilities:
  - durable workspace lifecycle
  - bounded repository evidence
  - AST replacement, patch application, and file replacement
  - allowlisted validation commands
  - repair loop
  - verified diff generation
  - durable evidence
- Authority boundary:
  - no remote GitHub mutation, merge, deployment, or rollback without founder governance
- V3 role:
  - execution capability selected by the unified reasoning and mission pipeline

### Company Brain foundation

- Current source: draft PR #392
- Proposed implementation areas:
  - `app/platform/events/event_sink.py`
  - `app/platform/company_brain/`
  - `app/platform/digital_twin/`
  - `app/platform/simulation/`
  - `app/platform/executive_ai/`
- Useful architecture:
  - neutral event sink
  - event observation after canonical persistence
  - downstream read-only projections
  - no write path back into production
  - feature-flagged composition
- Current limitations:
  - draft and not merged
  - based on an older main
  - process-local and in-memory
  - synchronous dispatch
  - placeholder simulation and executive interfaces
  - overlaps newer Executive Intelligence and reasoning work
- Decision:
  - do not merge PR #392 as-is
  - retain the neutral event-boundary concept
  - rebase and extract only the event contracts and projection patterns required by MC-KNOW-02
  - do not introduce another executive reasoning layer

## Canonical ownership table

| Concept | Canonical owner | Non-authoritative consumers |
|---|---|---|
| Founder conversation | Jarvis / Board Room | Executive Context summarizer |
| Conversation summaries | Executive Context | Executive Reasoning |
| Mission identity | Founder Approval `MISSION-*` | all downstream stages |
| Mission runtime state | PlatformWorkflowRun | Jarvis, Executive Intelligence, Journey Inspector |
| Worker execution state | PlatformAgentTask | Mission Runtime projections |
| Capability evidence | Capability Intelligence | Architecture Agent, Executive Reasoning |
| Architecture decision | Architecture Agent + Validator | Engineering Manager |
| Executive operational state | Executive Intelligence | Jarvis, dashboards, decision engine |
| Operational evidence | Operational Evidence persistence | Executive Intelligence, Validation, Reflection |
| Journey state | Journey Inspector read model | Reflection, Jarvis |
| Code change execution | Native Coding Agent | Mission Runtime |
| Repository mutation | Governed GitHub execution | Mission Runtime, PR lifecycle |
| Organizational events | neutral EventSink plus durable event adapter | Company Brain projections |
| Lesson candidates | MC-LEARN-01 reflection store | founder approval workflow |
| Executive principles | MC-PRINCIPLE-01 governed store | Executive Reasoning, Architecture Agent |

## Duplication risks

### High priority

1. Company Brain memory versus Executive Context
   - Resolution: Executive Context owns approved executive context; Company Brain stores organizational events and projections only.

2. Executive AI roles in PR #392 versus current Executive Reasoning and Executive Intelligence
   - Resolution: do not add parallel CEO, CTO, COO, and CFO reasoning services. Role-based views may be presenters or bounded evaluators behind the canonical reasoning pipeline.

3. Digital Twin placeholders versus existing sandbox and simulation capabilities
   - Resolution: MC-TWIN-01 must compose existing simulation, validation, repository, mission, and operational evidence. Do not promote placeholder interfaces into canonical ownership.

4. Company Brain event store versus operational evidence persistence
   - Resolution: operational evidence remains canonical evidence. Organizational events reference evidence rather than duplicate its payload and authority.

5. Mission history versus Journey Inspector
   - Resolution: Journey Inspector remains the canonical read model for mission progression. Company Brain may index mission events but does not redefine journey status.

### Medium priority

1. Executive Context versus browser conversation history
   - Browser history is UI convenience.
   - Executive Context is durable summarized context.

2. Capability registries versus Capability Intelligence
   - Existing registries remain declarations.
   - Capability Intelligence remains the composed evidence read model.

3. Architecture governance versus future Capability Evolution
   - Architecture Agent decides per mission.
   - MC-EVOLVE-01 produces platform-wide consolidation proposals.

## V3 knowledge lifecycle

```text
Founder conversation
→ bounded conversation summary
→ Executive Context
→ approved mission
→ PlatformWorkflowRun / PlatformAgentTask
→ operational evidence and Journey Inspector
→ organizational event
→ mission reflection
→ lesson candidate
→ founder review
→ approved executive principle
→ unified executive reasoning
→ future architecture and mission decisions
```

## Authority ranking

1. Constitution and governance policy
2. Founder-approved executive principles
3. Canonical durable operational state and evidence
4. Capability Intelligence and repository evidence
5. Mission and journey projections
6. Approved executive context
7. Conversation summaries
8. Model inference

Lower-ranked evidence cannot override higher-ranked authority.

## Locked V3 implementation order

1. MC-KNOW-02 — Governed Learning Integration
2. MC-LEARN-01 — Mission Reflection Engine
3. MC-PRINCIPLE-01 — Executive Principle Governance
4. MC-REASON-01 — Unified Executive Reasoning Pipeline
5. MC-EVOLVE-01 — Capability Evolution Engine
6. MC-TWIN-01 — Executive Digital Twin
7. MC-V3-01 — Company Operating System Integration

## MC-KNOW-02 implementation backlog

### K1 — Neutral durable organizational event contract

- Reuse the neutral EventSink direction from PR #392.
- Define versioned event envelopes.
- Emit only after canonical persistence succeeds.
- Include source authority, evidence references, mission identity, timestamps, and schema version.
- Prohibit events from becoming mission authority.

### K2 — Durable event adapter

- Replace process-local event storage with existing persistence infrastructure.
- Preserve failure isolation from canonical mission execution.
- Add idempotency keys and replay-safe persistence.
- Add feature flag with no-op default until validation passes.

### K3 — Mission lifecycle publishers

Publish normalized events for:

- mission approved
- workflow created
- task created
- stage changed
- change set verified
- PR created
- merge completed
- deployment completed
- verification completed
- mission blocked
- mission failed
- mission completed

### K4 — Context references, not copied authority

- Organizational events reference operational evidence IDs, workflow IDs, task IDs, PR numbers, revisions, and validation records.
- Do not copy or reinterpret canonical state as new truth.

### K5 — Company Brain projection boundary

- Add read-only mission timeline and organizational history projections.
- Reuse Journey Inspector for journey conclusions.
- Reuse Executive Intelligence for live executive state.
- Reuse Executive Context for approved executive context.

### K6 — Reasoning retrieval contract

Expose one bounded governed knowledge package containing:

- constitutional constraints
- approved executive principles when available
- approved executive context
- relevant capability intelligence
- relevant mission history references
- current executive state
- evidence freshness and unknowns

### K7 — Validation

Required checks:

- Python 3.9 compatibility
- event idempotency
- failure isolation
- replay safety
- no mission authority inversion
- no duplicate context store
- no duplicate operational evidence store
- no duplicate executive reasoning service
- runtime reconciliation
- Journey Inspector parity
- Board Room action flow
- Native Coding Agent compatibility

## Exit criteria for MC-V3-ARCH-01

- Canonical ownership is documented.
- Duplicate-system risks are explicitly resolved.
- PR #392 is classified as a source of patterns, not a merge-ready subsystem.
- MC-KNOW-02 has a concrete integration backlog.
- The V3 milestone sequence is validated and locked.

## Immediate execution decision

Start MC-KNOW-02 by extracting and rebasing the neutral event boundary from PR #392 onto current main, then connect durable mission runtime events to existing persistence and evidence references. Do not add lesson generation, executive principles, capability evolution, or Digital Twin behavior in the first PR.
