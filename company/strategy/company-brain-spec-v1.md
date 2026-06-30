# AI Software Factory Company Brain Specification v1.0

## Mission

Build the world's first AI-native software company that can think, remember, decide, learn, and build software through a governed executive operating system.

## Core principle

The company owns its knowledge. AI models do not.

AI models are interchangeable execution engines. The company's roles, decisions, governance, memory, and history must persist independently of any single chat, model, or vendor.

## Five capabilities

### 1. Think

The company understands problems before solving them.

Primary domains:

- Executive Office
- Product Strategy Office
- Board Room

Outputs:

- Vision
- Discovery notes
- Business cases
- Product requirements
- Roadmaps
- Proposals

### 2. Remember

The company preserves institutional memory.

Primary domains:

- Knowledge Vault
- Corporate Secretary
- Company Brain

Outputs:

- Board resolutions
- ADRs
- PRDs
- Policies
- Runbooks
- Standards
- Lessons learned

### 3. Decide

The company governs important action.

Primary domains:

- Executive Office
- Governance Engine
- Board Room

Outputs:

- Approvals
- Rejections
- Refinement requests
- Risk reviews
- Budget decisions
- Mission authorization

### 4. Build

The company executes approved missions.

Primary domains:

- Engineering Command
- AI Workforce
- Launch Center
- Quality Engineering

Outputs:

- Code
- Tests
- Documentation
- Deployments
- Release records

### 5. Learn

Every completed mission improves the company.

Primary domains:

- Knowledge Vault
- Corporate Secretary
- Executive Office

Outputs:

- Postmortems
- Metrics
- Lessons
- Updated standards
- Future recommendations

## Operating loop

The company must follow this operating loop:

1. Idea
2. Discovery
3. Proposal
4. Board Review
5. Approval
6. Mission
7. Execution
8. Deployment
9. Knowledge Update
10. Improvement

Engineering should not begin from a vague idea. Ideas must be clarified through Product Strategy and approved before becoming missions.

## Board Room

The Board Room is the persistent place where strategic discussion happens inside AI Software Factory.

A board meeting should capture:

- Meeting ID
- Date
- Participants
- Agenda
- Discussion summary
- Decisions
- Action items
- Linked ADRs
- Linked missions
- Status

The Board Room will eventually replace external chat as the primary place where the Founder and executive AI roles discuss company strategy.

## Corporate Secretary

The Corporate Secretary is responsible for preserving the company's thinking.

Responsibilities:

- Record board meetings
- Identify decisions
- Draft board resolutions
- Draft ADRs
- Update roadmap artifacts
- Link discussions to missions
- Maintain governance records
- Ensure important decisions are explainable

## Company Graph

The Company Brain should eventually maintain relationships between artifacts.

Example graph:

Founder Decision -> Board Resolution -> ADR -> Mission -> PR -> Deployment -> Knowledge Entry -> Future Recommendation

This allows the company to explain why work exists and how decisions produced outcomes.

## Executive roles

Executive roles belong to the company, not to individual AI models.

Initial persistent roles:

- CEO
- CTO
- Chief Product Officer
- CFO
- Corporate Secretary

Each role should eventually have:

- Responsibilities
- KPIs
- Inbox
- Mission queue
- Decision history
- Knowledge access
- Current objectives

## Autonomy levels

### Level 0: Founder controlled

The Founder directs all important work.

### Level 1: Company proposes

The company performs discovery and proposes work. The Founder approves.

### Level 2: Company recommends improvements

The company proposes ideas based on customer feedback, operational metrics, or technical debt. The Founder approves.

### Level 3: Governed low-risk autonomy

Low-risk improvements may proceed automatically under governance rules.

Examples:

- Documentation improvements
- Tests
- Internal dashboard refinements
- Non-breaking internal refactors

### Level 4: Governed continuous improvement

The company continuously proposes and executes improvements within defined governance boundaries.

## Constitution principles

1. The company owns its knowledge.
2. Ideas precede missions.
3. Every mission has a business purpose.
4. Every important decision is explainable.
5. Every completed mission teaches the company something.
6. Autonomy increases only through governance.
7. Executive roles are permanent; AI models are replaceable.
8. Code is replaceable. Company knowledge is not.

## Implementation direction

Company Brain starts as durable repository artifacts, then evolves into operational persistence through Cloud SQL and Mission Control APIs.

Initial implementation layers:

1. Repository-backed company artifacts
2. Mission Control API exposure
3. Cloud SQL persistence
4. Knowledge Vault retrieval
5. Board Room UI
6. Corporate Secretary automation
7. Governance Engine
8. Mission Engine

## Success criteria

The Company Brain succeeds when AI Software Factory can:

- Preserve strategic decisions outside chat history
- Explain why a mission exists
- Link discussions to decisions, missions, PRs, deployments, and lessons
- Let executive roles retain memory across AI model changes
- Run strategic discussions inside Mission Control
- Gradually increase autonomy through governance
