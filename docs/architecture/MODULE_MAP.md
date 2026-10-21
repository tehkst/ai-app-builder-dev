# Module map

Every top-level area of `app/`, its layer and status. Generated from
`app/platform/architecture_map.py` (`python -m app.platform.architecture_map --write`); CI fails if a
package is added or removed without updating the map. Statuses: **live** (production uses it),
**new** (built and checked, wired in by a coming roadmap step), **legacy** (live but replaced by
Orca; migrate, don't extend), **check-only** (only its own checks use it; retirement candidate),
**tooling** (validation and gates).

## Founder interfaces

What the founder sees and talks to: Mission Control, Jarvis, consoles.

| Area | Status | What it does |
|---|---|---|
| `board_room` | live | Jarvis: founder conversation, intent routing and executive reasoning. |
| `business_metrics` | live | Customers, sign-ups and MRR from the customer database. |
| `clients` | live | Clients area: agency clients, their code (safe fetch), Health Checks, PDF reports, jobs. |
| `cognitive_memory` | live | Memory and knowledge view (Insights page). |
| `conversation_intelligence` | live | Analyses founder conversations for Jarvis. |
| `customers_overview` | live | Customers screen data: customers joined with their apps. |
| `delivery_lineage` | live | Delivery history: how each mission went from idea to done. |
| `executive_decision` | live | Executive Decision Center (recommended actions). |
| `executive_office` | live | Executive Office summary for Mission Control. |
| `founder_console` | live | Founder console API (GCP-13). |
| `founder_decision` | live | Founder decision experience built on Jarvis responses. |
| `founder_workspace` | live | Founder workspace and request intake. |
| `journey_inspection` | live | Read-only end-to-end mission journey inspection. |
| `knowledge_vault` | live | Knowledge Vault summary. |
| `mission_control` | live | Mission Control summary API. |
| `operating_console` | live | Jarvis chat endpoint and its action buttons (Board Room actions). |
| `organization_console` | live | Organisation view: departments, workers, evidence (Insights page). |
| `repair_console` | live | Founder-only repair flow for customer app builds (/mission-control/repair/*). |
| `server` | live | The production app (app.platform.server:app): every route. |
| `telegram` | live | Telegram approval messages. |
| `ui` | live | Server-rendered pages: Mission Control (ui/mc2) and its Insights pages, Customer Portal, landing. |
| `ui_ux_agent` | live | Jarvis-proposed UI/UX changes with preview, approve, PR. |
| `ai_workforce` | legacy | Deprecated /mission-control/workforce adapter; use organization_console. |

## Orchestration

Decides what work happens and in which order.

| Area | Status | What it does |
|---|---|---|
| `orca` | live | Orca: missions, Builder <-> QA (+UX) loop, gates, store, API, CLI. The orchestrator. |
| `delegation` | legacy | Dynamic delegation services; mostly unused by production. |
| `engineering` | legacy | Engineering operating-system primitives (change sets). |
| `engineering_manager` | legacy | Engineering Manager planning layer. |
| `execution` | legacy | Older mission execution lifecycle (UI retired in step 3b; checks still use it). |
| `founder_approval` | legacy | Founder approval workflow (GCP-04). |
| `founder_workflow` | legacy | Founder workflow engine (FWE-01). |
| `management` | legacy | Engineering management hierarchy. |
| `mission_execution` | legacy | Mission execution bridge (GCP-05). |
| `organization` | legacy | Organisation hierarchy of the legacy agents. |
| `pipeline` | legacy | Older mission operating system (platform missions). |
| `planning` | legacy | Older autonomous engineering planning. |
| `pmo` | legacy | Programme management office; mostly unused by production. |
| `proposal_generator` | legacy | Proposal generator (GCP-03). |

## AI workforce

The AI employees (Orca's workforce lives in company/workforce/).

| Area | Status | What it does |
|---|---|---|
| `agents` | legacy | Legacy role agents, registry and worker, plus many checks; Orca's workforce replaces them. |

## Execution engine

Lets an employee act safely: tool loop, coding, GitHub, sandboxes.

| Area | Status | What it does |
|---|---|---|
| `ci_repair` | live | CI repair loop (GCP-16). |
| `coding_agent` | live | Governed edit/test/repair loop for platform changes; Stage D qualification. |
| `digital_twin` | live | Sandbox runner with resource limits. |
| `github` | live | GitHub integration and health. |
| `github_execution` | live | Approved GitHub execution: branches, commits, PRs, merges (its classic panel retired in step 3b). |
| `guards` | live | Filesystem write guard for generated files. |
| `nautilus` | live | Nautilus: tool-calling agent loop, permissions, recipes, provider adapters. |
| `repo_import` | live | Import external repositories for Jarvis to read. |
| `repository_intelligence` | live | Repository intelligence (GCP-09). |
| `workspaces` | live | Generated-app workspace roots. |
| `container_sandbox` | new | Locked-down Docker sandbox for running client code: copy only, no network, non-root, limits. |
| `autonomous_engineering` | legacy | Autonomous engineering worker (GCP-08). |
| `code_planner` | legacy | Guarded code planner (GCP-10). |
| `patch_application` | legacy | Guarded patch application (GCP-11). |
| `pr_orchestration` | legacy | Pull request orchestration (GCP-12). |

## Providers, data and knowledge

AI providers, persistence, company knowledge and evidence.

| Area | Status | What it does |
|---|---|---|
| `architecture_agent` | live | Platform-aware architecture decision support. |
| `architecture_knowledge_graph` | live | AST-derived architecture graph, size rule, relevance CLI. |
| `billing` | live | Billing plans catalogue (used for MRR). |
| `capability_intelligence` | live | Evidence-based capability inventory (never guesses). |
| `company_brain` | live | Company Brain: constitution, strategy, decisions. |
| `company_graph` | live | Company graph projection. |
| `company_intelligence` | live | Company intelligence snapshot. |
| `company_objects` | live | Company object model. |
| `config` | live | Application settings from the environment. |
| `credential_vault` | live | Encrypted credentials (KMS) with masked display. |
| `events` | live | Governed event contracts and emission. |
| `executive_intelligence` | live | Executive briefing and evidence registry (AEL-01). |
| `persistence` | live | Platform database models, sessions and migrations. |
| `plugins` | live | Vendor-neutral plugin architecture for providers. |
| `registry` | live | Unified platform registry for resource discovery. |
| `repository` | live | Shared repository loading and Markdown parsing. |
| `runtime` | live | AI provider selection (OpenAI, DeepSeek) and job runtime primitives. |

## Governance and safety

Who may do what: auth, approvals, policies, guards.

| Area | Status | What it does |
|---|---|---|
| `auth` | live | Founder login, sessions, password reset; customer auth. |
| `auth_boundary` | live | Authentication boundary policy (PROTECT-01). |
| `constitution` | live | Platform constitution and its runtime bindings. |
| `governance_authorization` | live | Canonical governance authorization boundary. |
| `validation` | live | Evidence-derived platform validation missions. |
| `security` | check-only | Rate limiting helpers. |

## Customer product

What customers use: the Customer Portal and their app builds.

| Area | Status | What it does |
|---|---|---|
| `app` | live | Root package. |
| `app.api` | live | Customer Portal API (/api/projects, auth). |
| `app.core` | live | Customer database and security core. |
| `app.models` | live | Customer database models: organisations, users, memberships, projects. |
| `app.schemas` | live | Customer API schemas. |
| `app.services` | live | Customer-side services. |
| `publish_review` | live | Customer publish requests: approve, reject, open PR. |
| `saas_builder` | live | Customer app builds: scope, generate, review, preview. |
| `services` | live | Shared services used by the customer pipeline and Jarvis (scoping, repair, workflows). |
| `codebase_health` | new | Codebase Health Check for client code: read-only scorecard and PDF (CLI; Mission Control next). |
| `app.ai` | check-only | Older generation graph and trusted templates; only checks use it. |

## Deploy and operations

Hosting, deployment, health and logging.

| Area | Status | What it does |
|---|---|---|
| `deployment` | live | Cloud Run deployment, preview and teardown (paused: no host). |
| `gcp` | live | GCP readiness and deploy gates (project deleted; kept until a new host). |
| `health` | live | Health status. |
| `logging` | live | Structured request logging. |
| `release` | live | Release actions and probes. |
| `repair` | check-only | Repair report listing tools. |

## Tooling and checks

Validation, gates and CI helpers.

| Area | Status | What it does |
|---|---|---|
| `adminops` | check-only | Demo admin operations flow. |
| `api` | check-only | Remaining helpers of the retired app/main.py API (platform admin auth, schemas); only checks use them. |
| `api_gateway` | check-only | Enterprise API gateway foundation (never served). |
| `catalog` | check-only | Catalogue models. |
| `collab` | check-only | Demo collaboration flow. |
| `data` | check-only | Data events, tenants, readiness and recovery primitives. |
| `feed` | check-only | Demo feed flow. |
| `integration` | check-only | Shared UX integration foundation. |
| `knowledge` | check-only | Engineering knowledge graph primitives. |
| `launch` | check-only | Demo launch flow. |
| `learning` | check-only | Decision learning primitives. |
| `lifecycle` | check-only | Lifecycle stage catalogue. |
| `memory` | check-only | Engineering memory scopes. |
| `notify` | check-only | Demo notices flow. |
| `onboarding` | check-only | Demo onboarding flow. |
| `operations` | check-only | Operations centre primitives. |
| `opscenter` | check-only | Demo operations centre flow. |
| `preferences` | check-only | Demo preferences flow. |
| `projects` | check-only | Project platform module. |
| `readiness` | check-only | Demo readiness flow. |
| `saas_portal` | check-only | Earlier customer portal foundation (superseded by ui/customer_home). |
| `self_healing` | check-only | Platform health control loop. |
| `webconsole` | check-only | Platform admin web console foundation (never served). |
| `work` | check-only | Demo work flow. |
| `workspace` | check-only | Demo workspace flow. |
| `a140_144` | tooling | Milestone alias that runs a registered check. |
| `api_contract` | tooling | Checks the server registers every expected endpoint. |
| `architecture_map` | tooling | This map of every area, layer and status (CI and docs only). |
| `architecture_map_check` | tooling | Keeps this map and docs/architecture/MODULE_MAP.md in step with the code. |
| `artifacts` | tooling | Generated-artifact stability checks. |
| `c135_139` | tooling | Milestone alias that runs a registered check. |
| `company_brain_check` | tooling | Company Brain check. |
| `compatibility` | tooling | Dependency policy and compatibility scanner. |
| `d1_1` | tooling | Milestone alias that runs a registered check. |
| `d1_2` | tooling | Milestone alias that runs a registered check. |
| `d1_3` | tooling | Milestone alias that runs a registered check. |
| `d1_4` | tooling | Milestone alias that runs a registered check. |
| `f126` | tooling | Milestone alias that runs a registered check. |
| `frontend` | tooling | Frontend build validation. |
| `import_integrity_check` | tooling | Fails CI if any file imports an app.* module that does not exist. |
| `l158_160` | tooling | Milestone alias that runs a registered check. |
| `n127` | tooling | Milestone alias that runs a registered check. |
| `o129` | tooling | Milestone alias that runs a registered check. |
| `o145_149` | tooling | Milestone alias that runs a registered check. |
| `p128` | tooling | Milestone alias that runs a registered check. |
| `r150_153` | tooling | Milestone alias that runs a registered check. |
| `r154_157` | tooling | Milestone alias that runs a registered check. |
| `release_gate` | tooling | Release gate runner. |
| `security_report` | tooling | Security report check. |
| `validate_all` | tooling | Runs every registered check by profile (CI uses --profile ci). |
| `w130_134` | tooling | Milestone alias that runs a registered check. |
| `z125` | tooling | Milestone alias that runs a registered check. |

Totals: 69 live, 2 new, 19 legacy, 28 check-only, 27 tooling.
