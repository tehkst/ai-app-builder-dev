# V86 — Railway/Gcore Deployment Pack

V86 makes the AI Software Factory repository ready for a first private hosted MVP deployment.

This milestone adds real deployment-preparation files, but it does not execute a live deployment.

## Files Added

- `Dockerfile`
- `.dockerignore`
- `railway.json`
- `docs/DEPLOYMENT_PACK_V86.md`
- `app/platform/agents/deployment_pack_v86_check.py`

## Safety Boundary

V86 is deployment-preparation only.

It must not:

- call Railway APIs
- call Gcore APIs
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

## Recommended First Provider: Railway

Railway is the recommended first provider for a private MVP because it can connect to GitHub, build from a Dockerfile, attach PostgreSQL, and manage environment variables quickly.

### Railway Setup Steps

1. Create a new Railway project.
2. Connect the GitHub repository.
3. Select the `main` branch after V86 is merged.
4. Let Railway build using the root `Dockerfile`.
5. Add a Railway PostgreSQL service.
6. Set environment variables from `.env.example`.
7. Use Railway's generated PostgreSQL connection string for both:
   - `DATABASE_URL`
   - `PLATFORM_DATABASE_URL`
8. Set production secrets:
   - `JWT_SECRET_KEY`
   - `PLATFORM_INTERNAL_TOKEN`
   - `PLATFORM_ADMIN_USERNAME`
   - `PLATFORM_ADMIN_PASSWORD`
   - `OPENAI_API_KEY`
9. Keep `HOSTED_SANDBOX_PROVIDER=local_only` until hosted sandbox execution is intentionally enabled in a later milestone.
10. Deploy.
11. Visit `/health` after deployment.
12. Run the production config healthcheck from the hosted environment if available.

## Railway Config

`railway.json` currently defines:

- health check path: `/health`
- restart policy: `ON_FAILURE`
- max restart retries: `10`

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

## Gcore Notes

Gcore is a later option for stronger infrastructure control or regional/security choices.

Expected Gcore path:

1. Create an app/container service.
2. Build from the root `Dockerfile`.
3. Provide PostgreSQL or an external PostgreSQL URL.
4. Configure the same production environment variables.
5. Keep `HOSTED_SANDBOX_PROVIDER=local_only` until hosted sandbox execution is intentionally implemented.
6. Confirm persistent storage and sandbox isolation before enabling generated-app runtime hosting.

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
RAILWAY_PROJECT_ID=replace_if_used
RAILWAY_TOKEN=replace_if_used
GCORE_PROJECT_ID=replace_if_used
GCORE_API_TOKEN=replace_if_used
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

V87 should perform the first end-to-end hosted MVP launch smoke after the deployment pack is merged and the selected provider is configured.
