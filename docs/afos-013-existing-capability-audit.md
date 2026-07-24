# AFOS-013 Existing Capability Audit

## Audit Basis

AFOS-013 was audited from canonical `main` at
`58e755ff19ed645b35317d5512f637cd753fdcbf` after the CI validation profile
passed. A module is classified as live only when implementation, registration,
persistence, invocation, UI exposure, tests, and Production configuration
support that conclusion.

The current Production baseline is revision
`ai-software-factory-production-00158-5dx` at 100% traffic. Health and
readiness pass. The visible build identity matches `58e755ff`.

## Principal Findings

1. `PlatformWorkflowRun` and `PlatformAgentTask` are the canonical durable
   workflow and task records.
2. Board Room mission approval already creates one deterministic durable
   workflow run and queues canonical agent tasks.
3. Planning, architecture review, engineering breakdown, executable change
   sets, governed GitHub execution, PR observation, merge, deployment,
   rollback, and Production verification exist.
4. `app.platform.execution.service` remains a process-local execution mission
   and evidence store. The durable mission worker still calls orchestration
   code that depends on it. This is the first canonical-state discontinuity.
5. The Native Coding Agent is implemented and independently durable through
   `PlatformAgentTask`, but the durable Board Room mission path currently calls
   executable change-set generation instead of the Native Coding Agent.
6. AFOS-006 provides a read-only continuation projection over later lifecycle
   evidence, but it is not the worker that advances the canonical durable
   workflow.
7. Durable artifact primitives exist, but there is no versioned delivery
   artifact contract linking product definition, UX, architecture,
   engineering, release, verification, and acceptance.
8. No canonical persisted founder release-acceptance record or founder-facing
   acceptance transition was found.
9. Several older workflow, release, deployment, and app-build families overlap
   conceptually. They must not become AFOS-013 state authorities.

## Delivery Stage Matrix

| # | Delivery stage | Expected outcome | Existing module/service | Entry point | Persistence authority | UI entry point | Governance boundary | Runtime / Production / tests | Known gap and duplication risk | AFOS-013 disposition |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Founder idea capture | Durable founder objective | Board Room operating console and conversation contract | Board Room chat endpoint | `PlatformContextStore` for structured decision state; browser chat is presentation cache | Jarvis | Founder authentication | Live in Production; AFOS-008 through 012.1 checks | Raw chat is not the durable product specification | CONNECT EXISTING |
| 2 | Product decisions | One material decision at a time | `founder_decision.service` | decision-experience state/action endpoints | Existing `PlatformContextStore` row | Inline chat decision and Executive Brief | Non-consequential founder decision | Live; AFOS-012 and 012.1 checks | Decision values are not linked to a mission artifact after approval | EXTEND EXISTING |
| 3 | Assumption confirmation | Versioned accepted/deferred assumptions | `founder_decision.service` | decision action endpoint | `PlatformContextStore` selection events | Inline controls and natural-language selection | Founder decision | Live and refresh-safe | References do not flow into canonical mission runtime | CONNECT EXISTING |
| 4 | Product definition | Structured approved definition | No canonical delivery artifact; partial proposal/decision structures exist | None canonical | None canonical | Executive Brief only | Founder approval for material scope | Not implemented end to end | Chat/brief can be the only specification; adding a second store is high risk | BUILD MISSING CAPABILITY |
| 5 | Mission proposal | Bounded objective, scope, exclusions, risks | Founder decision builder and Board Room actions | operating-console response/action | Decision state plus signed action context | Jarvis action card | Founder decision | Live | Proposal lacks canonical delivery artifact reference | EXTEND EXISTING |
| 6 | Mission approval | Scoped authoritative approval | `founder_approval.service`, operating-console action service | mission action endpoint | Existing approval evidence and operational evidence | Approve Mission | Founder approval | Live; action-flow checks | Approval must carry delivery contract references | EXTEND EXISTING |
| 7 | Mission creation | Exactly one canonical mission and workflow | `mission_run_service.accept_mission_run` | mission action endpoint | `PlatformWorkflowRun` state step | Jarvis / Mission Execution | Valid founder token and signed context | Live, deterministic and idempotent | Calls process-local execution mission during preparation | REPAIR EXISTING |
| 8 | Planning | Mission-specific engineering plan | `planning.service` through execution orchestrator | Durable worker prepare stage | Currently copied into process-local execution evidence and workflow state | Mission Execution progress | Autonomous after mission approval | Implemented and tested; Production invocation exists | Process-local evidence authority interrupts restart-safe reuse | REPAIR EXISTING |
| 9 | Product requirements | Durable PRD/requirements artifact | Planning output contains partial scope and criteria | No canonical artifact entry point | None canonical | Not exposed as a durable artifact | Autonomous drafting; founder decision for material changes | Partial only | Missing structured artifact and downstream reference | BUILD MISSING CAPABILITY |
| 10 | UX specification | Durable screens/workflows/states/accessibility | No canonical UX delivery stage found | None | None | None | Autonomous drafting | Missing | Existing UI generation utilities are not a mission UX authority | BUILD MISSING CAPABILITY |
| 11 | Architecture | Validated mission architecture and reuse decision | `architecture_agent.service` via architect specialist | durable prepare workflow | Copied into process-local mission evidence and workflow state | Mission Execution progress | Autonomous; cannot authorize writes | Implemented, registered, tested | Needs durable artifact/reference independent of process memory | CONNECT EXISTING |
| 12 | Engineering breakdown | Execution-ready task and validation plan | `engineering_manager.service` | orchestrator prepare stage / API | Copied into process-local evidence and workflow state | Mission Execution progress | Autonomous | Implemented and tested | Must consume canonical upstream artifacts and persist output | CONNECT EXISTING |
| 13 | Repository selection or creation | Bound repository identity | Repository Intelligence plus GitHub executor default repository | repository inspection / governed executor | Execution evidence and request metadata | Settings / execution panels | Repository mutation approval for creation | Existing repo binding works; repository creation parity exists elsewhere | Canonical mission does not persist repository binding early | EXTEND EXISTING |
| 14 | Workspace creation | Isolated durable workspace | `workspaces` services and Native Coding Agent session | coding agent start/integration | Workspace registry and coding session evidence | Agents / execution surfaces | Workspace boundary policy | Implemented and tested | Not invoked by durable Board Room mission worker | CONNECT EXISTING |
| 15 | Coding-agent execution | Real bounded edits in isolated workspace | Native Coding Agent | coding-agent integration endpoints / `PlatformAgentTask` | `PlatformAgentTask`, coding session/evidence | Agents; not coherent in Mission Execution | Approved scope; no direct main | Implemented, feature-gated, tested | Durable mission path uses change-set generator instead | CONNECT EXISTING |
| 16 | Edit/test/repair loop | Bounded repair with evidence | Native Coding Agent service/session and `ci_repair` | coding agent execution | Coding session/task evidence | Technical details only | Autonomous within approved scope and limits | Implemented and qualification-tested | Not connected to canonical mission continuation | CONNECT EXISTING |
| 17 | Change-set creation | Verified diff compatible with repository executor | Native Coding Agent `VerifiedDiff`; legacy engineering change set | coding agent result / change-set service | Task result and execution evidence | Mission Execution | No repository write yet | Both formats exist and compatibility tests exist | Two producers; legacy path is canonical in mission worker today | CONSOLIDATE DUPLICATES |
| 18 | Repository mutation approval | Scoped authorization | Governance Authorization and approved GitHub executor | preview/execute endpoints | Governance approval/evidence records | GitHub Execution / Jarvis action | Exact scoped approval | Implemented and tested | Mission continuation must use one authority and one scope | CONNECT EXISTING |
| 19 | Branch and commit | Feature branch and commit only | Approved GitHub executor / platform execution layer | governed execute | GitHub plus operational evidence | Executions | Repository mutation approval; direct-main blocked | Implemented and tested | Not driven by canonical durable worker | CONNECT EXISTING |
| 20 | Pull-request creation | One PR linked to mission | Approved GitHub executor | governed execute | GitHub and execution evidence | Executions | Same scoped repository authorization | Implemented, idempotency evidence partial | Durable mission link relies on process-local execution evidence | REPAIR EXISTING |
| 21 | PR review | Readable lifecycle and review evidence | PR lifecycle service and governed GitHub capabilities | PR status endpoint | GitHub plus operational evidence | PR Lifecycle | Read-only; approval for review mutations | Implemented and tested | Review outcome is not a canonical workflow artifact | CONNECT EXISTING |
| 22 | CI execution | Observe required checks | PR lifecycle check-runs and validation architecture | PR status / validation profiles | GitHub checks and validation results | PR Lifecycle | Read-only | Implemented | No canonical durable transition from PR to CI state | CONNECT EXISTING |
| 23 | CI repair | Classify and repair bounded failures on same PR | `ci_repair` and Native Coding Agent repair loop | service calls, no unified mission entry | Existing execution/task evidence | Not coherently exposed | Autonomous within approved scope and retry limits | Components and checks exist | Integration into same PR and durable run is incomplete | CONNECT EXISTING |
| 24 | Security validation | Security/release validation evidence | validation architecture and security checks | validation profiles | Validation output/evidence | Technical details | Mandatory release gate | Implemented | Not linked as delivery artifact | CONNECT EXISTING |
| 25 | Acceptance validation | Product/release acceptance evidence | validation profiles and production verification checks | validation service/profile | Validation evidence | Mission/verification panels | Mandatory gate | Implemented in parts | No unified mission acceptance artifact | CONNECT EXISTING |
| 26 | Merge approval | Scoped founder authorization | Approved merge and Governance Authorization | merge preview/execute | Approval/evidence records | Merge panel / Jarvis | Exact merge approval | Implemented and tested | Needs canonical continuation wiring | CONNECT EXISTING |
| 27 | Merge | Merge approved PR only | `approved_merge` / GitHub execution authority | merge execute | GitHub and operational evidence | Merge panel | Governed execution | Implemented | Mission evidence linkage is projection-only | CONNECT EXISTING |
| 28 | Deployment preparation | Release/deploy plan and target | Release flow, deployment preview | release/deployment services | Release store and operational evidence | Deployment panel | Read-only until execution | Implemented | Multiple legacy release/deployment families; canonical production path is approved Cloud Run | CONSOLIDATE DUPLICATES |
| 29 | Deployment approval | Scoped founder authorization | Governance Authorization and approved Cloud Run | deployment preview/execute | Approval/evidence records | Deployment panel / Jarvis | Exact deployment approval | Implemented and tested | Needs canonical workflow action projection | CONNECT EXISTING |
| 30 | Deployment | Cloud Run deploy | `approved_cloud_run` | deployment execute endpoint | Cloud Run plus operational evidence | Deployment panel | Governed execution | Live and used for releases | Not advanced by durable mission worker | CONNECT EXISTING |
| 31 | Traffic movement | Explicit revision traffic | Governance execution layer / rollback service | governed action | Cloud Run plus evidence | Deployment/Rollback | Separate governed approval | Implemented | Must remain separate from general deployment authority | REUSE AS-IS |
| 32 | Health and readiness | Service readiness evidence | `/health`, `/ready`, deployment health checks | health endpoints | Runtime observation | Production status | Read-only | Live in Production | Needs linkage to release and mission | CONNECT EXISTING |
| 33 | Production verification | Evidence-based deployed checks | `deployment.production_verification` | verification endpoint and automatic verifier | `PlatformOperationalEvidence` | Verification panel | Founder auth for manual run; read-only | Implemented, persisted, tested | Does not produce founder acceptance | EXTEND EXISTING |
| 34 | Founder acceptance | Persisted accept/fix/rollback/defer result | No canonical implementation found | None | None | None | Founder decision | Missing | Completion can be claimed before founder acceptance | BUILD MISSING CAPABILITY |
| 35 | Rollback | Approved traffic rollback | `approved_rollback` | rollback preview/execute | Cloud Run and operational evidence | Rollback panel | Exact rollback approval | Implemented and tested | Keep separate scope; link evidence to delivery contract | CONNECT EXISTING |
| 36 | Project memory and artifact retention | Reconstructable project history | Company Brain, context store, workflow/task records, workspace artifacts, operational evidence | Multiple read models | Several existing durable tables | Projects, History, Mission Execution | Read-only unless governed mutation | Components exist | No canonical delivery artifact index; evidence is fragmented | EXTEND EXISTING |
| 37 | Resumability after failure or restart | Resume without duplication | `PlatformWorkflowRun`, deterministic tasks, leases, owner fencing | mission status/continue and worker activation | Workflow/task tables | Mission Execution | Restored founder session for sensitive work | Implemented through change-set-ready; checked | Later delivery stages and process-local execution evidence are not restart-complete | REPAIR EXISTING |

## Canonical Authorities to Preserve

| Concern | Canonical authority |
|---|---|
| Founder decision state | Existing `PlatformContextStore` decision record |
| Founder approval | Existing Founder Approval and Governance Authorization services |
| Mission workflow state | `PlatformWorkflowRun` mission state |
| Executable work | `PlatformAgentTask` and canonical Agent Worker |
| Planning | Existing Planning service |
| Architecture | Existing Architecture Agent |
| Engineering breakdown | Existing Engineering Manager |
| Code editing and repair | Existing Native Coding Agent |
| Repository/PR mutation | Existing governed GitHub execution authority |
| PR/CI observation | Existing PR lifecycle service |
| Merge | Existing approved merge authority |
| Deployment | Existing approved Cloud Run authority |
| Traffic rollback | Existing approved rollback authority |
| Production verification | Existing Production Verification service |
| Cross-cutting authorization | Existing Governance Authorization Layer |

## Duplicate and Legacy Risk

- `app.platform.execution.service._ACTIVE_MISSION` is process-local and cannot
  remain an authority in the durable delivery chain.
- Founder Workflow cards, Mission Pipeline aggregation, and AFOS-006 mission
  continuation are projections. They must not own lifecycle state.
- The legacy executable change-set generator and Native Coding Agent overlap.
  Native Coding Agent is the canonical edit/test/repair authority; compatibility
  with the existing repository change-set contract should be retained.
- Generic app-build, release, deployment engine, runtime, and lifecycle
  packages contain useful capabilities but must not supersede the approved
  GitHub, merge, Cloud Run, rollback, and verification authorities used by
  Mission Control.

## Evidence-Based AFOS-013 Scope

AFOS-013 should not build a new orchestrator or store. The smallest coherent
scope is:

1. add a versioned delivery contract and delivery artifacts inside the
   existing durable workflow state;
2. move planning, architecture, and engineering evidence ownership from the
   process-local execution mission into that workflow state;
3. route approved implementation through the Native Coding Agent;
4. extend the existing mission worker/continuation path to project governed
   repository, PR/CI, merge, deploy, verification, and acceptance stages;
5. persist founder acceptance in the same workflow state and expose the
   integrated projection in existing Mission Execution and Jarvis surfaces.

