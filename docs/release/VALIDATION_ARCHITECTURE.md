# Validation Architecture

## Purpose

AI Software Factory validation is target-aware. A platform source release, a
generated application, a live AI generation qualification, and a production
deployment do not have the same prerequisites and must not be represented by
one unconditional command.

The authoritative machine-readable catalogue is:

```bash
python3 -m app.platform.validate_all --list
```

## Profiles

| Profile | Command | Runs where | Cloud required | Secrets required | Release meaning |
|---|---|---|---|---|---|
| Local | `python3 -m app.platform.validate_all --profile local` | Developer workstation | No | No | Mandatory platform source baseline |
| CI | `python -m app.platform.validate_all --profile ci` | Pull-request CI | No | No | Mandatory platform source regression gate |
| Production reference | `python3 -m app.platform.validate_all --profile production` | Local or CI before release | No | No | Validates production configuration contracts and secret references, never secret contents |
| Generated artifact | `python3 -m app.platform.validate_all --profile artifact` | Workspace containing a generated application | No | No | Mandatory only when qualifying a generated application artifact |
| AI integration | `python3 -m app.platform.validate_all --profile ai-integration` | Explicit integration environment | Provider network | `OPENAI_API_KEY` | Mandatory only for live AI generation qualification |

Missing declared Python packages are environment setup failures. Install
`requirements.txt` before running local or CI validation. Validators do not
silently skip an applicable check because a package is missing.

## Platform Checks

The local, CI, and production-reference profiles run the same deterministic
platform source checks:

| Group | Checks | Type | Mandatory |
|---|---|---|---|
| Compatibility | `compatibility_scanner`, `compatibility_scanner_contract`, `dependency_policy` | Regression | Yes |
| Validation contract | `validation_architecture` | Regression | Yes |
| API and workflow | `platform_routes`, `workflow_tracking_engine` | Smoke | Yes |
| Agent and organization foundations | `v100_workflow`, manifests, organization, memory, knowledge, management, PMO | Regression | Yes |
| Governance and runtime | constitution, delegation, runtime, recovery, event bus, self-healing | Regression | Yes |
| Platform services | plugins, registry, deployment, operations, admin, API gateway, SaaS, lifecycle, billing | Regression | Yes |
| Authentication | `auth_foundation`, `login_boundary` | Regression and smoke | Yes |
| AFOS intelligence | Executive Intelligence, Founder Workflow, Conversation Intelligence, Executive Decision | Regression | Yes |
| Legacy compatibility packs | V124 through V160 | Regression | Yes while still present on current architecture |
| Deployment contracts | Docker, PostgreSQL/Redis, environment/secret references, health/readiness, structured logging | Regression and smoke | Yes |

`login_boundary` verifies the authenticated safe-shell fallback by patching the
current dashboard render boundary. AFOS intelligence checks validate current
contracts and behavior rather than retired milestone labels or UI wording.

## Generated-Application Checks

These checks are not applicable when no generated application workspace exists:

| Check | Purpose | Type |
|---|---|---|
| `frontend_contract` | Generated frontend authentication and safe-error contract | Regression |
| `frontend_build` | Generated frontend build | Build |
| `security_report` | Generated backend/frontend security baseline | Regression |
| `artifact_registry` | Generated artifact inventory | Artifact integrity |

They remain strict in the `artifact` profile. Absence of the generated
application is not reported as a platform source regression.

## Live AI Checks

`generation_graph` invokes the external model provider and may generate
workspace artifacts. It is isolated in `ai-integration` because it requires
provider connectivity and `OPENAI_API_KEY`. Local and ordinary PR validation
must not require Production provider secrets.

The check must receive credentials through the execution environment. Secret
values must never be printed, committed, or copied from Production.

## Cloud and Production Checks

Static cloud architecture checks run without cloud credentials:

- `app.platform.gcp.check`
- `app.platform.gcp.readiness`
- `app.platform.gcp.deploy_check`
- `app.platform.d1_3`

They validate the Dockerfile, the deploy workflow's Cloud Run deploy and
health-check steps, expected configuration names, and deployment contracts.
They do not read secret values.

Cloud-authenticated operations belong only to the manually dispatched
`.github/workflows/platform-deploy.yml` workflow. Workload Identity and
environment variables authorize image publication, deployment, and
post-deployment checks. There is no Terraform layer — Cloud Run, Cloud SQL,
Secret Manager, and Artifact Registry resources are provisioned directly in
the GCP project, and the workflow only builds/publishes the image and updates
the Cloud Run service revision. Production smoke tests validate the deployed
service URL, revision, health, readiness, and founder-facing surfaces after
deployment.

## Release Gates

Platform release:

```bash
python3 -m app.platform.release_gate --mode full --target platform
```

This runs the internal import guard and the complete CI platform profile.

Generated-application release:

```bash
python3 -m app.platform.release_gate --mode full --target generated-app \
  --artifact-path /path/to/canonical/generated-application
```

This additionally requires generation stability, artifact drift, and the
generated-artifact profile. `--artifact-path` is the canonical qualification
input; the historical CRM fixture remains only a backward-compatible default.
The gate is expected to fail when its artifact or live generation prerequisites
are absent.

## Failure Classification

Every failure must be classified as exactly one of:

- **A — Real software defect**
- **B — Broken validation**
- **C — Obsolete validation**
- **D — Environment configuration**
- **E — Missing local dependency**
- **F — External service dependency**
- **G — Intentional Production-only dependency**

Skipped checks are not passes. They are explicitly non-applicable to the
selected profile and remain mandatory in their owning profile.
