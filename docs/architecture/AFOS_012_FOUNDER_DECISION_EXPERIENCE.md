# AFOS-012 Founder Decision Experience

## Purpose

AFOS-012 turns the Board Room's structured AFOS-011 response into a
decision-ready founder workspace. It does not replace AFOS-009 reasoning,
AFOS-010 executive intelligence, AFOS-011 conversation orchestration, or the
Mission Runtime.

## Runtime flow

```text
Founder message
  -> FounderConversationContract
  -> ContextRetriever
  -> JarvisCognitiveCore (AFOS-009 and AFOS-010)
  -> FounderResponseComposer (AFOS-011)
  -> Founder Decision builder
  -> FounderChatPresentation
  -> chat and Executive Brief
```

The visible chat and Executive Brief receive the same
`founder-decision-v1` document. Simple informational responses do not create a
decision document.

## State ownership

Decision state is stored as bounded JSON in the existing
`PlatformContextStore`, scoped by conversation ID. This reuses the shared
transactional platform database and introduces no new table or parallel
mission registry.

Card updates use:

- founder authentication;
- a conversation-specific scope;
- optimistic version checks;
- a row lock during transition;
- bounded idempotency keys;
- one database transaction.

The browser's local conversation history remains a presentation cache. The
durable decision document is restored from the backend and remains
authoritative.

## Governance

Non-consequential decision edits use the Founder Decision service. Mission
approval does not use that service. It continues through the existing signed
Board Room action context and founder-authenticated Mission Runtime path:

```text
Mission proposal card
  -> operating-console/action
  -> founder approval
  -> deterministic mission identity
  -> durable workflow run
  -> platform agent task
```

Confirming an assumption never starts a mission.

## Founder effort

The response layer defaults preparatory actions to Jarvis. The founder is
asked for a decision only when an assumption is both uncertain and material.
Customer discovery recommendations prepare target profiles, questions,
prototypes, and evidence scoring before requesting founder review.

## Failure behavior

- Duplicate card actions return the unchanged durable state.
- Stale versions return a founder-safe conflict and the current document.
- Network and action failures leave the prior state intact.
- Mission governance errors are returned by the canonical mission action
  service.
- No tokens, credentials, chain-of-thought, or full raw founder prompts are
  stored in the decision document.

## Known limits

- The Assumption Engine currently uses bounded conversation and domain
  inference; richer Company Brain evidence can be added through the existing
  context boundary.
- Card actions update the brief immediately. A richer conversational event
  transcript can follow without changing state ownership.
- Browser-local chat history is not itself cross-device durable; the
  structured decision brief is.
