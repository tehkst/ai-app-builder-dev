# Orca: the orchestrator (`app/platform/orca/`)

*Why the name:* an orca pod hunts as a coordinated team led by a matriarch who knows every
member's role. Orca leads the AI employees through each mission.

Orca is roadmap steps 2-3 of `company/strategy/ai-workforce-plan.md` at minimum viable size: a
workforce registry and an **executing** orchestrator. Unlike `agents/orchestrator.py` (fixed
plan) and `pipeline/mission_pipeline.py` (read-only view), Orca dispatches employees, checks their
work and loops until quality gates pass. The process is adapted from the NEXUS playbook in
[agency-agents](https://github.com/msitarzewski/agency-agents) (MIT).

## How a mission runs

1. **Start** with a goal and a generated-app workspace inside `APPROVED_SANDBOX_ROOT_BASE`.
2. **Plan:** the architect inspects the workspace (read-only) and returns a summary plus 1-8
   tasks, each with acceptance checks (single shell commands that exit 0 when done).
3. **Execution decision:** if any task has checks and execution wasn't pre-approved, the mission
   pauses at `awaiting_execution_approval`. The founder approves (checks and builder commands may
   run in the workspace) or declines (Orca still builds and reviews, but can't verify at runtime).
4. **Build ↔ QA loop**, per task:
   - the builder implements it (writes allowed; commands only if execution is approved);
   - acceptance checks run (only if approved);
   - the QA lead reviews read-only and returns PASS/FAIL, evidence and issues;
   - the task passes only if QA says PASS, no blockers are listed **and** every executed check
     passed. A failing check overrides a QA PASS;
   - on FAIL the builder gets the QA findings and failed-check output; after 3 attempts the task
     and the mission are **escalated** with every attempt's handoffs.
5. **Integration gate:** all checks re-run together → `complete`, or `escalated` if something
   that passed earlier now fails. If execution was declined → `complete_unverified`.

**Provider outages pause, they don't fail.** If the AI provider errors (missing key, outage,
timeout) the mission becomes `paused` with `paused_reason`; no Dev↔QA attempt is used up (a QA
outage redoes the whole attempt). `run` resumes it. **Founder retry:** `retry` gives an escalated
task a fresh set of attempts, keeping its history.

Orca itself is deterministic code; only employees use the model. State is saved after every step
(JSON in `ORCA_MISSION_DIR`, default `/tmp/ai-software-factory/orca/missions/`), so `run` resumes
a mission after a restart; an interrupted attempt counts toward the 3.

## Employees

`company/workforce/manifest.yaml` + `roles/*.md` (loaded by `workforce.py`). An employee's
`permission_mode` is a ceiling: Orca never grants more, and without execution approval no
employee runs a non-read-only command. Today: `architect` (plans), `builder` (builds), `qa_lead`
(reviews). Orca finds them by `responsibilities` (`plan_mission`, `build_task`, `review_task`), so
an employee can be replaced by editing the manifest.

## Using it

```bash
python -m app.platform.orca start --goal "Add a /health endpoint returning ok" \
    --workspace /tmp/ai-software-factory/workspaces/demo
python -m app.platform.orca approve ORCA-XXXXXXXXXXXX   # or: decline
python -m app.platform.orca status ORCA-XXXXXXXXXXXX
python -m app.platform.orca retry ORCA-XXXXXXXXXXXX    # escalated task: another round
```

In code: `Orca().start_mission(...)`, `.decide_execution(...)`, `.run(mission_id)`.

## Not done yet

- **No API/Mission Control UI** yet; CLI and Python only.
- **No live-model mission test.** `orca_check.py` uses a scripted pod; a live DeepSeek mission
  check (ai-integration profile) is the next verification step.
- **Mission state is JSON files**, not the platform DB; migrate when missions need querying.
- **Only 3 employees and one pipeline shape.** Next: specialist routing (frontend/backend/database
  builders, security review), more NEXUS phases (discovery, hardening, launch), parallel tasks,
  and wiring the Nautilus repair flow in as the "fix production issue" mission type.
- **Not yet connected** to `agents/registry.py`, the agent task queue, the Board Room or the
  approval-gate services; the execution decision is Orca's own record.

## Checks

`orca/orca_check.py` (in `validate_all`): full mission with a check-driven retry, restart/resume,
escalation after 3 failures, provider outages at each stage pause and resume
without using attempts, founder retry of an escalation, declined execution (checks never run), workspace and planning guard
rails, permission ceilings.
