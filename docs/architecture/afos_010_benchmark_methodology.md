# AFOS-010 Benchmark Methodology

## Sets

1. Original regression set: the 100 AFOS-009 prompts are preserved unchanged.
2. Holdout set: 50 prompts frozen in `app/platform/board_room/afos_010_holdout_benchmark.py` after implementation. They cover strategy, comparison, diagnosis, architecture, product, creativity, challenge, uncertainty, action boundaries, compound constraints and implementation.
3. Contrast families include discussion versus implementation, negative constraints, conditional mission creation and explicit mission preparation.
4. Existing AFOS-008 tests cover pending proposal approval, durable mission creation and idempotency across turns.

## Deterministic evaluation

Deterministic checks evaluate mode, action availability, mission-trigger precision/recall, leakage, unauthorized execution, context-source relevance, canonical decision-path invocation, Tier 0 bypass, perspective bounds, provider call bounds and absence of duplicate authority.

They do not award qualitative points for required phrases. The holdout hard gates are exact behavioral assertions.

## Qualitative evaluation

The A/B packet randomizes response order independently for every prompt. Each record stores both responses, preference, scores, rationale and failure classification. The current evaluator is a deterministic structural proxy, explicitly labeled low confidence. No model credential or independent human panel was available in this environment, so human-level quality targets are not claimed as passed.

## Fixtures and limitations

The reproducible fixture provides identical read-only context and an intentionally malformed provider response. This forces fallback and isolates architecture, routing and safety. It does not measure normal DeepSeek synthesis, token use or model latency. Healthy-provider integration is covered separately and proves one provider call, compact brief injection and no fallback.

The legacy AFOS-009 keyword-weighted rubric is retained for historical comparison but is not treated as an objective intelligence score. It rewards surface phrases and therefore cannot establish judgment quality.

## Release target status

| Gate | Result |
|---|---|
| Mission-trigger precision | 1.0, passed |
| Mission-trigger recall | 1.0, passed |
| Unauthorized execution | 0, passed |
| Prompt/reasoning leakage | 0, passed |
| Phantom mission creation | 0, passed |
| Exact benchmark hard-coding | None found |
| Qualitative holdout targets | Not demonstrated; independent evaluator unavailable |
| Provider token delta | Not available without configured provider |
| Healthy provider call delta | No extra call |
| Rejected draft bound | One revision maximum |

## Required follow-up for credible 8.7+ claims

Run the frozen packet with the production-selected DeepSeek model, capture latency and token telemetry without prompt leakage, and use an independent blinded human or model evaluator. Do not modify routing or fallbacks after opening the holdout packet.
