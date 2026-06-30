# Company Object Model

AI Software Factory is built around Company Objects, not files, prompts, or isolated APIs.

Files, database rows, API responses, UI components, and AI context are representations of Company Objects.

## Initial object types

- Board Meeting
- Decision
- Resolution
- Mission
- ADR
- Policy
- Executive
- Roadmap Item
- Product
- Customer
- Deployment
- Incident
- Lesson

## Universal fields

Every Company Object should eventually have:

- Object ID
- Object type
- Version
- Title
- Status
- Owner
- Summary
- Tags
- Relationships
- History
- Permissions
- AI summary

## Relationship examples

- Board Meeting creates Decision
- Decision becomes Resolution
- Resolution creates Mission
- Mission produces PR
- PR produces Deployment
- Deployment produces Lesson
- Lesson informs future Decision

## Principle

Company Objects form the foundation of the Company Graph. This allows Mission Control to explain why work exists, how decisions were made, and what outcomes followed.
