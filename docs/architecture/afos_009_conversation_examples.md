# AFOS-009 Conversation Evidence

These examples describe the regression-tested founder presentation. Internal routing, prompts, context, and critic signals are intentionally absent.

Rendered evidence:

- [Natural conversation](afos_009_natural_conversation.png): direct Agents answer with no action card.
- [Decision-ready mission](afos_009_decision_ready_mission.png): implementation request with Approve Mission, Edit Scope, and Reject.

## Agents Question

**Before:** A fixed executive recommendation with mission-oriented headings and approval language.

**After:** Jarvis explains that the current UI exposes three summary groups rather than the complete agent directory, labels the richer-runtime conclusion as inference, and gives a product opinion. No action card is rendered.

## Strategic Discussion

**Before:** The question was converted into a recommendation card.

**After:** Jarvis takes a position on exposing registered agents, discusses visibility versus governance-controlled editing, and creates no mission.

## Direct Implementation Request

**Before:** Implementation and conversational requests could enter similar recommendation prose.

**After:** A direct “Fix the Agents page” request produces an effort estimate and the existing Approve Mission, Edit Scope, and Reject controls. Execution remains blocked pending approval.

## Natural Approval

**Before:** Bare approval could produce more generic recommendation prose without launching the intended durable mission.

**After:** “Approve” launches only the signed pending recommendation from the same conversation. It creates one durable mission and workflow run; repetition returns the same workflow run. Without pending context, Jarvis asks what is being approved.

## Capability Question

**Before:** Capability questions could consult stale mission continuity.

**After:** Jarvis lists the governed lifecycle it can support and its approval limits without loading mission history or rendering actions.

## Limitation Question

**Before:** Limitations shared the broad Board Room path.

**After:** Jarvis directly explains that it cannot self-approve, bypass policy, claim unverified completion, expose secrets, or treat capability as authority.
