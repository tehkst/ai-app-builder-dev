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

**Execution policy** (`execution_policy.py`). Founder approval allows running the app's tests,
not arbitrary commands. Like the controlled runtime's command allowlist, Orca only executes test
runners (`pytest`, `python -m pytest`, `python -m unittest`, `npm test`, `npm run test|build|lint`)
and read-only inspection, with every path inside the workspace; `python -c`, `node -e`, scripts and
network tools are refused, for acceptance checks and builder commands alike. The architect must give
every task at least one allowed check (one corrective round, then the mission fails), and a mission
is only `complete` (verified) when every task has checks and all pass. This is a command policy, not
an OS sandbox: allowed test runners still execute generated tests with the platform user's rights.
Container isolation is on the roadmap.

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
employee runs a non-read-only command. Each has a founder-facing `summary`, shown in Mission
Control under "Your AI team".

| Employee | Responsibility | Role |
|---|---|---|
| Software Architect | `plan_mission`: plans tasks, gives each a `specialty` (frontend/backend/general) and checks | planner |
| Builder | `build_task`, `build_task:backend`, `build_task:general` | builder |
| Frontend Developer | `build_task:frontend`: pages, components, forms; accessible and responsive | builder |
| QA Lead | `review_task`: works as asked, with evidence | reviewer |
| UX Designer | `review_ux`: reviews **frontend** tasks after QA passes (clarity, flow, states, WCAG 2.2 AA) | reviewer |

Routing: a task goes to the employee with `build_task:<specialty>`, falling back to `build_task`.
A frontend task passes only when QA **and** the UX Designer pass it; UX findings go back to the
builder on the next attempt (retry briefings only carry the previous attempt's findings). Replace
or add employees by editing the manifest.

Note: employees work on **generated-app workspaces**, never on the platform itself (including
Mission Control), by design (`FACTORY_CODE_IMMUTABILITY_RULE`).

## Using it

**From Mission Control** (`/mission-control/ui`, nav item "Orca Missions", `#orca`): start a mission
(goal + workspace from the approved sandbox folder, optional pre-approval of test runs), watch it
progress (the page polls every 5 s and only redraws on change), approve/decline execution, resume a
paused mission, retry an escalated task, and read every task's builder summaries, QA verdicts,
issues, check output and the timeline. All mission text is HTML-escaped.

**API** (`orca/api_service.py`, registered in `app/platform/server.py`): founder-only POSTs with the
Mission Control session token in the body, like other governed actions:
`/mission-control/orca/missions`, `/mission`, `/workspaces`, `/start`, `/decide-execution`, `/run`,
`/retry`. Long work runs in a background thread per mission (`orca/runner.py`); a crash pauses the
mission with the error. Runs are in-process: after a server restart a mission shows "Not currently
running" and the founder clicks Run.

**From the Board Room:** Board Room proposals are platform missions by default, and Orca only works
on generated apps. So a proposal gets a "Build it in '<app>' with the AI team (Orca)" button
(`operating_console/action_service._orca_buttons`) only when the request names exactly one existing
app workspace as a whole word and doesn't mention the platform (Mission Control, Jarvis, Board
Room, Orca, Nautilus, platform). It opens Orca Missions with the goal and that workspace filled in
and a "From the Board Room" note; the founder presses Start, so nothing starts without that click. The mission records
`started_from_board_room` with the proposal's `MISSION-…` id and shows a "from Board Room" tag.

**CLI:**

```bash
python -m app.platform.orca start --goal "Add a /health endpoint returning ok" \
    --workspace /tmp/ai-software-factory/workspaces/demo
python -m app.platform.orca approve ORCA-XXXXXXXXXXXX   # or: decline
python -m app.platform.orca status ORCA-XXXXXXXXXXXX
python -m app.platform.orca retry ORCA-XXXXXXXXXXXX    # escalated task: another round
```

In code: `Orca().start_mission(...)`, `.decide_execution(...)`, `.run(mission_id)`.

## Not done yet

- **Background runs are in-process** (one server process): no queue/worker, no auto-resume after restart.
- **No OS-level isolation** for executed tests (see Execution policy); run them in containers next.
- **Mission state is JSON files**, not the platform DB; migrate when missions need querying.
- **Five employees, one pipeline shape.** Next: database and security specialists, more NEXUS
  phases (discovery, hardening, launch), parallel tasks, and the Nautilus repair flow as a "fix
  production issue" mission type.
- **Not yet connected** to `agents/registry.py`, the agent task queue or the approval-gate
  services; the execution decision is Orca's own record.

## Checks

- `orca/api_check.py`: the real production app (`app.platform.server:app`) with a founder token:
  auth required, workspace validation, start -> decision -> complete, retry after escalation, crash
  -> paused, dashboard includes the view, and `node --check` on the view's JavaScript (if node exists).
- `orca/live_mission_check.py`: a real mission on DeepSeek (`deepseek-v4-flash`) in CI step
  "Orca live mission" and the `ai-integration` profile. A fresh FastAPI demo gets a `/health`
  endpoint plus a unittest; the result is verified independently of Orca.

- `orca/orca_check.py` (in `validate_all`): full mission with a check-driven retry, restart/resume,
escalation after 3 failures, provider outages at each stage pause and resume
without using attempts, founder retry of an escalation, declined execution (checks never run), workspace and planning guard
rails, permission ceilings.
