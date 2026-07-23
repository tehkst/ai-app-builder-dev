# AFOS-010 Canonical Authority Map

| Responsibility | Canonical owner | AFOS-010 treatment | May mutate? |
|---|---|---|---:|
| Request decomposition | `RequestDecomposer` | Reused | No |
| Conversation mode and depth | `ConversationModeClassifier` | Reused; semantic families expanded | No |
| Context relevance | `ContextRetriever` | Reused; product strategy source matrix narrowed | No |
| Executive decision reasoning | `ExecutiveDecisionEngine` | Reused and reconnected | No |
| Decision contract adaptation | `RecommendationGenerator` | Reused | No |
| Perspective selection | `ExecutivePerspectiveSelector` | Reused; maximum three perspectives | No |
| Cognitive orchestration | `ExecutiveIntelligenceOrchestrator` | New thin adapter, no reasoning algorithm | No |
| Provider synthesis | `JarvisCognitiveCore` and `JarvisPromptBuilder` | Reused with compact brief | No |
| Response quality | `ExecutiveResponseCritic` | Reused with bounded judgment signals | No |
| Browser presentation | `FounderChatPresentation` | Unchanged whitelist boundary | No |
| Mission approval | Existing operating-console action service | Unchanged | Governed |
| Mission persistence | Existing mission-run / workflow-run persistence | Unchanged | Governed |
| Workflow execution | Existing Factory Runtime | Unchanged | Governed |
| GitHub, merge, deploy, rollback | Existing capability and governance services | Unchanged | Governed |

## Permanent boundary

Executive intelligence may inspect, evaluate, recommend and synthesize. It cannot create or approve a mission, execute a workflow, mutate GitHub, merge, deploy, roll back, move traffic, persist authority, or bypass founder governance. Capability remains separate from authority.

## Compatibility dispositions

- `ResponsePresenter`: deterministic compatibility and legacy non-conversational presentation.
- Executive Board Room v2: existing API/mission deliberation compatibility; its fixed consensus is not canonical decision reasoning.
- AFOS-002 Executive Decision Center: workflow action router, not the substantive executive decision engine.
- Executive Office: read-model adapter over Executive Intelligence.
- Historical `executive_ai` CEO/CTO/COO/CFO package: absent from current main and not recreated.
