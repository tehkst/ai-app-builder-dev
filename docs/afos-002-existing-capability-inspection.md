# AFOS-002 Existing Capability Inspection Report

## Scope

Inspect existing decision, conversation, workflow, approval, mission, governance, and UI capabilities before implementation.

## Existing capabilities confirmed

- Conversation Intelligence: `app/platform/conversation_intelligence/service.py`
  - Classifies founder intent into architecture, roadmap, implementation, deployment, security, strategy, research, knowledge, and general modes.
  - Produces structured semantic decisions, actions, knowledge, workflow type, mission requirement, and roadmap proposals.
- Executive Decision Center: `app/platform/executive_decision/service.py`
  - Selects contextual next actions for incidents, deployment reviews, roadmaps, engineering proposals, discussion, knowledge capture, and no action.
- Founder Workflow Engine: `app/platform/founder_workflow/service.py`
  - Owns visible workflow cards, workflow stages, founder approval gates, roadmap-specific approval meaning, deployment approval, and governance constraints.
- Board Room and Operating Console
  - Already invoke conversation intelligence and executive decision services through Mission Control routes.
- Mission Pipeline
  - Already observes mission, PR, deployment, verification, and completion state.
- Governance
  - Founder approval, feature-branch-only mutation, no direct main writes, and deployment review are already enforced.

## Duplication review

AFOS-002 must not add:

- another conversation classifier;
- another executive decision engine;
- another workflow engine;
- another approval model;
- another mission registry;
- another UI shell.

## Extension points

1. Extend `decide_next_action` to return a guided workflow contract aligned to the existing Founder Workflow Engine.
2. Map each contextual executive action to an existing workflow type and initial stage.
3. Preserve planning-only semantics for roadmap approval.
4. Preserve explicit founder approval before repository mutation or deployment.
5. Add deterministic checks for incident, roadmap, implementation, deployment, knowledge, and no-action flows.

## Architecture decision

AFOS-002 is an integration enhancement across existing services. The Executive Decision Center remains the action selector; the Founder Workflow Engine remains the workflow and approval authority; Conversation Intelligence remains the intent source.
