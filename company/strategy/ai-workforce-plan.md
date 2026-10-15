# AI Workforce Plan

Status: proposed (2026-10-15). Owner: founder. Source reviewed:
[msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) (MIT, 270 agent
role prompts in 17 divisions, plus the NEXUS multi-agent playbook in `strategy/`).

## Goal

AI Software Factory is an AI company staffed by AI employees: each employee knows its own job,
an orchestrator runs the show, and the company runs itself, with autonomy widening only through
governance (constitution principle 6).

## Where we are (honest baseline, 2026-10-15)

- **Roles exist, depth doesn't.** 16 role agents (`app/platform/agents/skills/*/skills.md`),
  ~13 lines each: purpose, capabilities, boundaries. Most specialist handlers in
  `agents/specialists/` are deterministic code, not model-driven work.
- **No executing orchestrator.** `orchestrator.py` emits a fixed 5-task plan;
  `builtin.orchestrator_agent` returns static advice ("child_task_creation:
  planned_for_next_version"); `pipeline/mission_pipeline.py` is a read-only aggregator whose
  "auto-completed" stages are labels, not work.
- **Execution engine now exists.** Nautilus (`app/platform/nautilus/`) is a model-driven tool loop
  with permissions, recipes and retry-until-checks-pass, verified live against DeepSeek in CI.
  First adopter: the generated-app repair flow (PR #539).
- **Strong governance.** Approval gates, sandbox guards, audit, validation suite.

**Conclusion:** the bottleneck is not the number of roles, it is (1) an orchestrator that actually
dispatches work and loops until quality gates pass, and (2) employees that can actually do work.
Importing all 270 prompts now would add 270 more personas that, like today's 16, have no way to act.

## Decision: onboard 63 of 270, in three waves

Onboard by business need and only when the orchestrator can use them. Adapt rather than copy:
each prompt is rewritten into our house format (role, mission, tools, permission mode, autonomy
tier, handoff contract, definition of done) and credited to agency-agents (MIT).

### Do not onboard (~207)

Domains we don't operate in: academic (6), game-development (21), gis (13), healthcare (3),
spatial-computing (6); region/platform-specific marketing (Douyin, Xiaohongshu, WeChat, Weibo,
Bilibili, Baidu, ...); stack-specific engineers we don't use (Drupal, WordPress, Solidity,
ServiceNow, Feishu, GaussDB, WeChat Mini Program, ...); personal/consumer roles (Aging Parent Care,
Study Abroad, Personal Growth, Real Estate, Resume Tailor, ...). Revisit only if a customer app
needs one. The Agency Agent Factory (`agent_factory_agent`) can propose them on demand later.

### Wave 1: Build the product (the software factory itself)

Upgrade the existing 16 with agency-agents prompts, and add the roles the build pipeline lacks.

| Our employee | Status | Adapt from agency-agents |
|---|---|---|
| orchestrator_agent (Chief Operating Officer) | upgrade, becomes the real orchestrator | Agents Orchestrator + NEXUS playbook |
| ceo_agent | upgrade | Chief of Staff (operating cadence), Business Strategist |
| cto_agent | upgrade | Software Architect, Multi-Agent Systems Architect |
| architect_agent | upgrade | Software Architect, Backend Architect |
| engineering_manager_agent | upgrade | Senior Project Manager, Project Shepherd |
| builder_agent | upgrade | Senior Developer, Rapid Prototyper |
| frontend_builder_agent / frontend_manager_agent | upgrade | Frontend Developer, UI Designer, UX Architect |
| backend_builder_agent / backend_manager_agent | upgrade | Backend Architect, API Platform Engineer |
| database_builder_agent / database_manager_agent | upgrade | Database Optimizer, Database Reliability Engineer |
| reviewer_agent | upgrade | Code Reviewer |
| test_agent | upgrade | Test Automation Engineer, API Tester |
| quality_manager_agent | upgrade, owns quality gates | Reality Checker, Evidence Collector |
| code_steward_agent | upgrade | Codebase Onboarding Engineer, Technical Writer |
| agent_factory_agent | upgrade | Multi-Agent Systems Architect, Prompt Engineer |
| repair_agent | **new** (Nautilus repair proposer) | Minimal Change Engineer |
| security_agent | **new** | Application Security Engineer, AI-Generated Code Security Auditor |
| devops_agent | **new** | DevOps Automator, SRE (Site Reliability Engineer) |
| design_agent | **new** | UX Architect, UI Designer, Accessibility Auditor |
| performance_agent | **new** | Performance Benchmarker |

### Wave 2: Run the platform (operate safely without the founder in the loop)

Incident Response Commander, Infrastructure Maintainer, FinOps Engineer, Automation Governance
Architect, Agentic Identity & Trust Architect, Secrets & Credential Hygiene Engineer, Compliance
Auditor, Privacy Engineer, Legal Compliance Checker, Model QA Specialist, Prompt Engineer,
Workflow Optimizer, Tool Evaluator, Payments & Billing Engineer.

### Wave 3: Grow the business

Product Manager, Sprint Prioritizer, Feedback Synthesizer, Trend Researcher, UX Researcher,
Growth Hacker, SEO Specialist, Content Creator, Developer Advocate, Brand Guardian, Customer
Success Manager, Support Responder, Sales Engineer, Proposal Strategist, Pricing Analyst, Chief
Financial Officer, Bookkeeper & Controller, Analytics Reporter, Executive Summary Generator.

## The orchestrator (adapted from NEXUS)

One executing orchestrator owns mission state and dispatches employees. Design:

- **Pipeline:** Discovery → Strategy & Architecture → Foundation → Build ↔ QA → Hardening →
  Launch → Operate. Each phase ends at a quality gate with explicit evidence.
- **Dev↔QA loop:** every task is built, then checked by the quality owner; FAIL returns to the
  builder with the QA findings; max 3 attempts, then escalate with a failure report.
- **Handoffs:** structured, using NEXUS handoff templates (context, deliverable, quality
  expectations, verdict + evidence) so each employee gets complete context.
- **Employees run on Nautilus:** an employee = role prompt + tool set + permission mode +
  recipe(s). Checks in recipes are the machine-verifiable definition of done.
- **State is durable:** missions, tasks, handoffs and verdicts persist in the platform DB and
  `company/missions/`, never only in memory, so the company survives restarts.

## Autonomy tiers (constitution principle 6)

| Tier | Runs without the founder | Examples |
|---|---|---|
| 0 Observe | always | read code, analyse logs, plan, draft |
| 1 Sandbox | always, inside a generated-app sandbox | write files, run tests in sandbox, propose repairs |
| 2 Reversible | after quality gate passes | open PRs, deploy to staging, apply approved-plan repairs |
| 3 Irreversible / external | founder approval, until the board grants a standing rule | merge to main, production deploy, spend money, contact customers, change credentials |

Autonomy grows by moving specific actions down a tier through a recorded board resolution
(`company/board/resolutions/`), backed by evidence that the gate has held.

## Build order

1. Workforce registry: `company/workforce/` with adapted role files + a manifest mapping each
   employee to department, tools, permission mode, autonomy tier; loader registers them as
   `AgentDefinition`s with a Nautilus-backed handler.
2. Executing orchestrator implementing the pipeline, Dev↔QA loop and handoffs above, on top of
   the existing agent task queue (`services/agent_task_service`, `agents/worker.py`).
3. Wave 1 employees, one end-to-end mission: founder intent → shipped PR, with gates.
4. Autonomy tiers enforced in code (permission policy + approval gates read the tier).
5. Waves 2 and 3.
