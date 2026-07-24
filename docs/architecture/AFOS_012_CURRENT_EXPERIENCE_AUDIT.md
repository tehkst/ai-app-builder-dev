# AFOS-012 Current Experience Audit

## Current flow

```text
Founder message
  -> Board Room chat endpoint
  -> AFOS-011 conversation contract
  -> relevance-gated context
  -> AFOS-009 cognitive core
  -> AFOS-010 executive intelligence
  -> founder response composer
  -> FounderChatPresentation
  -> chat bubble and Executive Brief
```

## Findings

- AFOS-011 produces structured decisions, actions, and mission proposals, but
  they exist only as response objects. There is no canonical assumption,
  alternative, trade-off, risk, or decision-request model.
- The Executive Brief flattens artifact objects into list text. It duplicates
  prose instead of presenting decision state, and empty sections remain
  visible.
- Browser history persists message snapshots in `br_ui_sessions_v2`. It
  isolates chats locally, but it is not durable cross-instance decision state.
- `PlatformContextStore` already provides shared transactional context
  persistence and can store a bounded decision document under a
  conversation-specific scope. A new table or mission registry is unnecessary.
- Mission approval already uses signed action context, founder authentication,
  durable approval evidence, deterministic mission identity, and reusable
  workflow runs. AFOS-012 must call this path rather than create another
  mission transition.
- Recommendation and assumption controls do not exist. The few current action
  buttons either call mission actions or append local notes; generic note
  buttons do not persist backend state.
- Proposed and accepted states are distinguishable in the data but are not
  rendered as functional stateful cards.
- Conversation history is bounded and isolated, but structured brief state is
  not restored independently after refresh.
- The current responsive breakpoint stacks the Executive Brief below the
  conversation. It remains a long column and has no focused mobile control.
- Loading cleanup uses `finally` and is reliable for normal success/failure.
  Errors are founder-safe, though decision action conflicts need their own
  version-aware feedback.

## Reuse decisions

- Reuse AFOS-009, AFOS-010, and AFOS-011 for reasoning and response quality.
- Reuse `PlatformContextStore` for durable decision documents.
- Reuse Board Room signed mission actions for mission approval and idempotency.
- Extend the existing FounderChatPresentation; do not create a competing chat
  response.
- Add one authenticated decision-state boundary for non-consequential card
  transitions.
