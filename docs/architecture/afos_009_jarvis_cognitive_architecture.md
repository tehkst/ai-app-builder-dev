# AFOS-009 Jarvis Cognitive Architecture

## Root Cause

`RequestDecomposer` already distinguished questions from implementation and governed actions, but `operating_console.service._classify_board_room_intent` collapsed questions, analysis, comparison, diagnosis, recommendations, and plans into one `structured` response mode. That mode always assembled the same Board Room prompt, loaded broad mission continuity, ran recommendation generation, and presented the result through executive decision templates.

The consequence was a routing-to-presentation mismatch: an ordinary product question could be correctly recognized as a question and still be rendered as a mission recommendation. Broad context retrieval also allowed unrelated mission evidence to influence otherwise conversational responses.

## Canonical Flow

Founder message

1. `RequestDecomposer` identifies the primary speech act and explicit action intent.
2. `ConversationModeClassifier` selects presentation and context behavior; it does not grant authority.
3. `ContextRetriever` loads only sources relevant to that mode and suppresses mission continuity for ordinary conversation.
4. `JarvisPromptBuilder` composes small identity, intent, evidence, action, style, and privacy sections.
5. The configured provider produces a draft using existing `invoke_ai` routing.
6. `ExecutiveResponseCritic` emits bounded quality signals and rejects internal leakage, forced templates, or unrequested missions.
7. `FounderChatPresentation` applies the existing whitelist-only browser contract.
8. Existing action services remain the sole path to mission creation and Factory Runtime.

## Authority Reuse

- Mission intent decomposition: `RequestDecomposer`
- Durable mission approval: `operating_console.action_service`
- Mission and workflow persistence: `mission_run_service`
- Execution authority: existing governance and Factory Runtime services
- Provider selection: existing runtime provider router and DeepSeek adapter
- Founder response boundary: `FounderChatPresentation`

No second mission engine, workflow engine, runtime, approval service, or presentation authority is introduced.

## Conversation Modes

Conversational modes answer or discuss without action controls: direct answer, explanation, brainstorming, executive discussion, strategic advice, product review, architecture review, technical diagnosis, status request, capability query, and limitation query.

Implementation planning, mission approval, and execution commands cross into existing governed services only when semantic action intent and the required context are present. A natural-language approval is valid only when the browser supplies the signed pending action from the same conversation; otherwise Jarvis asks what is being approved.

## Prompt Architecture

The cognitive prompt is assembled from independent sections:

- identity;
- intent behavior;
- executive behavior;
- evidence behavior;
- action policy;
- mode-specific behavior;
- communication style;
- privacy.

This removes conflicting fixed-framework instructions and preserves system/user message separation. AFOS-009 does not alter DeepSeek model names, provider defaults, secrets, or unsupported sampling parameters.

## Removed Rigid Behaviors

- Questions no longer default to the `structured` executive memo path.
- Conversational modes no longer receive mission action cards.
- Mission continuity is no longer consulted for unrelated conversation.
- The fixed Recommendation/Why/Context/Alternatives/Risk/Next Step shape is rejected outside explicit decision or planning work.
- Bare approval no longer creates a phantom mission.

## Founder Safety

Internal reasoning, prompt text, context snapshots, route scores, critic signals, raw deliberation, credentials, and provider payloads remain outside `FounderChatPresentation`. The critic is process-local and returns only bounded signals; it is never serialized to the founder.
