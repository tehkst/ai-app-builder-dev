# AFOS-016 End-to-End Blocker Audit

## Audit scope

This audit traces the production composition root (`app.platform.server:app`) from
an application request through durable mission evidence, engineering, repository
execution, deployment, verification, and delivery lineage. It distinguishes the
canonical AFOS-013/015 path from the older platform-admin app-build preview path.

## Canonical path selected

Request
-> Founder/SaaS presentation
-> `software-delivery-v1`
-> `PlatformWorkflowRun`
-> `PlatformAgentTask`
-> delivery-contract artifacts
-> Native Coding Agent verified diff
-> governed GitHub execution
-> PR lifecycle and merge
-> governed Cloud Run deployment
-> production verification
-> AFOS-015 lineage projection

Canonical durable authorities are existing records:

- Mission/workflow: `PlatformWorkflowRun` with durable mission state in its
  `mission_run_state` step result.
- Work: `PlatformAgentTask`.
- Delivery artifacts: `software-delivery-v1` plus existing workspace artifacts.
- Repository mutation and PR: approved GitHub execution and GitHub evidence.
- Deployment and verification: existing deployment authority and
  `PlatformOperationalEvidence`.
- Replay: AFOS-015 projection over the preceding authorities.

## Existing duplicate or non-production paths

The platform-admin app builder under `app.platform.api.app_build` is not a
production authority. It is mounted by `app.main`, while the production
container starts `app.platform.server`. Its runner builds a separate four-step
agent workflow, defaults to simulation, and persists generated-file previews
without repository or deployment execution. AFOS-016 will not promote that
workflow to a second mission runtime.

The trusted full-stack CRM templates under `app.ai.templates` are reusable
starter evidence, but they are split frontend/backend scaffolds and are not a
deployed generated-application authority. AFOS-016 may select and adapt their
FastAPI/authentication conventions, but must expose one canonical reference
application template through the existing mission and coding path.

Legacy process-local execution state and generated-file preview records remain
non-authoritative. They must not determine SaaS Builder lifecycle state.

## Blocker matrix

| Journey stage | Canonical authority | Existing capability | Actual blocker | AFOS-016 action |
|---|---|---|---|---|
| End-user request | Existing auth/session boundary plus `software-delivery-v1` context | Founder request and Board Room actions create governed missions | No customer-facing SaaS Builder exists in the production composition root; existing builder is platform-admin-only | Add a thin customer presentation and authenticated request adapter that creates the canonical mission |
| Mission creation | `PlatformWorkflowRun` durable mission state | `accept_mission_run` creates deterministic durable run and initial `PlatformAgentTask` | Founder-only action context and presentation are assumed; workspace identity is not projected for a SaaS customer | Reuse mission creation and add bounded workspace/application metadata to mission context |
| Requirements | Delivery-contract product definition | Planning creates product definition and success criteria | Current artifact is founder-mission oriented and does not contain the complete generated-app specification contract | Extend the existing delivery artifact content; do not create a new registry |
| Architecture | Delivery-contract architecture artifact | Architecture Agent and Repository Intelligence run before engineering | Existing analysis targets the factory repository, not a canonical generated-app subtree/template | Select one reference template and give Architecture Agent the bounded generated-app target |
| Code generation | Native Coding Agent verified diff | Durable coding task, workspace, validation, repair, verified diff | Repository target is fixed to the factory root and no generated-app golden-path template is selected | Reuse Native Coding Agent and constrain changes to one generated-app subtree |
| Validation | Native Coding Agent validation evidence | Structural and command validation already gate verified diffs | No generated-app-specific acceptance suite or health/readiness contract | Add golden-path validation commands and acceptance criteria to the existing mission plan |
| Repair | Native Coding Agent bounded repair | Existing failure analysis and bounded repair iterations | Repair evidence is present but generated-app browser/deployment failures are not fed into the same mission continuation | Link generated-app verification failures back through existing repair evidence and budget |
| Repository execution | Approved GitHub execution | Branch, commit, push, PR, CI and mission markers exist | Repository is globally fixed to `tehkst/ai-app-builder-dev`; no explicit generated-app subtree policy | Use the existing repository as the canonical multi-application repository and authorize only the generated-app subtree |
| Deployment | Approved Cloud Run deployment | Governed `gcloud run deploy`, revision and URL evidence | Source is fixed to `.` and defaults describe the factory service; it cannot truthfully deploy a generated app separately | Generalize the existing authority with a bounded source directory and generated-app service policy |
| Browser verification | Production Verification plus browser acceptance tooling | HTTP health/readiness checks and browser control exist | Current verifier checks Mission Control branding/endpoints, not an application-specific owner/customer journey | Extend the existing verification authority with an application acceptance adapter |
| Live URL delivery | Delivery contract and SaaS presentation | Deployment can return a service URL and lineage can project it | No customer lifecycle projection or completion UI; factory URL can be mistaken for generated-app URL | Project lifecycle from canonical mission evidence and reveal live URL only after browser acceptance |

## First broken handoff

The first broken production handoff is the end-user request into the canonical
mission runtime. The only existing customer-looking app-build endpoint belongs
to the non-production `app.main` composition and launches a separate preview
workflow. It does not create the durable Board Room mission used by AFOS-013 and
AFOS-015.

## Downstream blockers

Even after mission creation, the existing GitHub and Cloud Run authorities are
factory-specific. Repository execution can safely target a generated-app
subtree in the existing repository, but deployment must accept that bounded
source directory and a distinct service identity. Production verification must
then verify the generated application contract rather than Mission Control.

## Minimal implementation direction

1. Add a SaaS Builder presentation and adapter to the production composition
   root.
2. Reuse deterministic durable mission creation with workspace/application
   metadata.
3. Select one generated application template under a canonical repository
   subtree.
4. Extend the existing deployment authority for a policy-bounded source
   directory and distinct service.
5. Extend existing verification evidence for the appointment-booking journey.
6. Project all customer progress and completion from the durable mission;
   AFOS-015 remains the replay authority.

No new workflow engine, mission table, application registry, provider router,
GitHub integration, deployment engine, verification store, or lineage store is
required.
