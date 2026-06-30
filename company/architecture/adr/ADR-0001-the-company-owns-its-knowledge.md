# ADR-0001: The Company Owns Its Knowledge

## Status

Accepted

## Date

2026-06-30

## Context

AI Software Factory began as a founder-led build process supported by external AI conversations. This created momentum, but it also exposed a strategic weakness: important company thinking, roadmap decisions, architectural rationale, and operating principles could remain trapped inside a single chat thread or model context.

That is not acceptable for a durable AI-native software company.

If AI Software Factory is to become a company that can think, remember, decide, learn, and build, its institutional memory must belong to the company itself.

## Decision

AI Software Factory will treat company knowledge as a first-class company asset.

The company, not any external AI model or temporary chat session, owns:

- Vision
- Constitution
- Strategy
- Roadmap
- Board decisions
- Architecture decisions
- Product decisions
- Missions
- Runbooks
- Lessons learned
- Executive role history
- Governance policies

AI models may assist with reasoning, drafting, coding, summarizing, and execution, but they do not own the company's memory.

## Consequences

### Positive

- Strategic decisions survive chat changes, context resets, and AI model changes.
- Executive roles can remain persistent even when the underlying AI model changes.
- The company can explain why decisions were made.
- Missions can be traced back to ideas, discovery, approvals, PRs, deployments, and lessons.
- Mission Control can become the primary place where company thinking happens.
- Knowledge can compound over time.

### Tradeoffs

- The company must invest in structured memory, not only code.
- Important decisions must be promoted into durable artifacts.
- The system must distinguish between discussion, draft thinking, and approved company memory.
- Governance is required to decide what enters official memory.

## Alternatives considered

### Keep strategy in external chats

Rejected. This makes the company dependent on fragile chat history and specific AI model contexts.

### Store only code and technical docs

Rejected. A self-improving company needs business memory, governance memory, product memory, and decision history, not only code.

### Rely only on vector memory

Rejected as the primary memory layer. Retrieval is useful, but the company also needs explicit, auditable, versioned artifacts.

## Implementation direction

Company memory starts in the repository through the `company/` directory and later expands into operational persistence through Cloud SQL, Mission Control APIs, Knowledge Vault retrieval, and Board Room workflows.

Initial memory layers:

1. Repository-backed company artifacts
2. Structured Company Brain documents
3. ADRs and board resolutions
4. Mission Control API exposure
5. Cloud SQL persistence
6. Knowledge Vault retrieval
7. Board Room and Corporate Secretary automation

## Related principles

- Code is replaceable. Company knowledge is not.
- Executive roles are permanent; AI models are replaceable.
- Ideas precede missions.
- Every important decision is explainable.
- Every completed mission teaches the company something.

## Related artifacts

- `company/README.md`
- `company/strategy/company-brain-spec-v1.md`
- `company/constitution/README.md`

## Outcome

Accepted as the first foundational architecture decision for the Company Brain program.
