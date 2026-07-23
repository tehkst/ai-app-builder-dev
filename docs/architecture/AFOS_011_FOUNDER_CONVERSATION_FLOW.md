# AFOS-011 Founder Conversation Flow

## Pre-change runtime path

```text
Founder Dashboard Board Room
  -> POST /mission-control/operating-console/chat
  -> constitution.board_room_binding.chat_with_operating_console
  -> operating_console.service.board_room_chat
  -> legacy intent classification
  -> ContextRetriever
  -> JarvisCognitiveCore (AFOS-009)
  -> ExecutiveIntelligenceOrchestrator (AFOS-010)
  -> runtime AI provider
  -> ExecutiveResponseCritic
  -> AFOS-010 deterministic fallback
  -> FounderChatPresentation
  -> Founder Dashboard
```

The CRM acceptance request entered the legacy technical-diagnosis mode. Context
retrieval included unrelated project progress. The model draft then failed the
AFOS-010 critic, and the deterministic fallback replaced it with a generic
position plus raw operational evidence. The response carried no structured
decisions or actions, leaving the Executive Brief empty.

## Canonical runtime path

```text
Founder Dashboard Board Room
  -> POST /mission-control/operating-console/chat
  -> constitution.board_room_binding.chat_with_operating_console
  -> operating_console.service.board_room_chat
  -> FounderConversationContract
  -> relevance-gated ContextRetriever
  -> JarvisCognitiveCore (AFOS-009)
  -> ExecutiveIntelligenceOrchestrator (AFOS-010)
  -> runtime AI provider
  -> ExecutiveResponseCritic
  -> FounderResponseComposer validation/repair
  -> FounderChatPresentation
  -> Founder Dashboard and Executive Brief
```

`FounderConversationContract` does not replace either intelligence layer. It
defines the requested outcome, relevant evidence sources, governance boundary,
response requirements, and permissible proposed artifacts. The cognitive core
continues to use AFOS-009 and AFOS-010 for planning, provider invocation, and
critique. `FounderResponseComposer` is the final presentation guard: it rejects
raw internal evidence, repairs an unsuitable draft, and emits proposed
decisions, actions, mission proposals, or knowledge only when the mode allows
them.

## Governance boundary

Advisory, discovery, review, and information modes cannot execute work.
Implementation or consequential requests remain approval-gated. Proposed
artifacts are not accepted authority and do not create missions, write code,
merge pull requests, deploy, or alter production.

## Conversation continuity

The browser sends only the active session's recent founder/Jarvis turns. The
history is bounded and sanitized before prompt construction. It improves
follow-up continuity but is not canonical mission state. Durable mission truth
continues to come from the existing workflow runtime.
