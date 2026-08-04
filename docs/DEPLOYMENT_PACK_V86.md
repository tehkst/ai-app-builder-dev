# V86 — Deployment Preparation (GCP Cloud Run)

V86 makes the AI Software Factory repository ready for a first private hosted MVP deployment.

This milestone adds real deployment-preparation files, but it does not execute a live deployment.

Update: the Railway and Gcore provider paths originally described in this milestone have been retired.
The platform's actual production deployment target is GCP Cloud Run - see "Actual Production Path"
below. The constitution (`app/platform/constitution/loader.py`) states plainly that "Railway is not
part of the production architecture."

## Files Added

- `Dockerfile`
- `.dockerignore`
- `docs/DEPLOYMENT_PACK_V86.md`
- `app/platform/agents/deployment_pack_v86_check.py`

## Safety Boundary

V86 is deployment-preparation only.

It must not:

- create cloud services
- spend money
- build Docker images automatically
- start Docker containers
- start Kubernetes workloads
- create public URLs
- run generated code
- bypass approval gates
- apply repairs
- roll out generated modules

## Actual Production Path: GCP Cloud Run

GCP Cloud Run is this platform's real, already-live production target. It is not a manual
per-provider console setup: deployment runs through `.github/workflows/platform-deploy.yml`
(`workflow_dispatch`, environment-scoped), whose `validate` job runs
`app.platform.gcp.check`/`readiness`/`deploy_check`/`environment_topology_check` and
`infra/scripts/gate.sh` before the `docker` job builds/pushes the image and the `deploy` job
runs `gcloud run deploy` with secrets wired from GCP Secret Manager via `--set-secrets` and
non-secret config via `--set-env-vars` (see that workflow file for the exact current list).
Visit `/health` after a deploy, and run the production config healthcheck.

## Docker Runtime

The root `Dockerfile`:

- uses `python:3.12-slim`
- installs `requirements.txt`
- copies the repository into `/app`
- exposes port `8000`
- starts FastAPI with Uvicorn

Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

## Required Environment Variables

Use `.env.example` as the source checklist.

Minimum production values:

```text
DATABASE_URL=
PLATFORM_DATABASE_URL=
JWT_SECRET_KEY=
PLATFORM_INTERNAL_TOKEN=
PLATFORM_ADMIN_USERNAME=
PLATFORM_ADMIN_PASSWORD=
OPENAI_API_KEY=
```

Deployment-provider placeholders:

```text
HOSTED_SANDBOX_PROVIDER=local_only
```

Do not commit real secrets.

## Validation

Run locally from the V86 branch:

```bash
git checkout milestone/v86-railway-gcore-deployment-pack
git pull origin milestone/v86-railway-gcore-deployment-pack

python -m py_compile app/platform/agents/deployment_pack_v86_check.py
python -m app.platform.agents.deployment_pack_v86_check
```

Expected result:

```text
'passed': True
```

Then return to main:

```bash
git checkout main
git pull origin main
```

## V87 Preview

V87 should perform the first end-to-end hosted MVP launch smoke after the deployment pack is merged and GCP Cloud Run is configured.
