# Production Infrastructure

This directory contains the Google Cloud deployment foundation for AI Software Factory.

## Structure

- `scripts/` contains operator entrypoints for validation.

Cloud Run, Cloud SQL, Secret Manager, and Artifact Registry resources are
provisioned directly in the GCP project and deployed via
`.github/workflows/platform-deploy.yml`, which authenticates through GitHub
OIDC (Workload Identity Federation) and drives `gcloud` directly. There is no
Terraform layer — IAM bindings and infrastructure changes are applied by hand
against the project and the deploy workflow only publishes images and updates
the Cloud Run service revision.

## Runtime secrets are attached directly to the Cloud Run service

The production service's runtime secrets (`DATABASE_URL`, `PLATFORM_DATABASE_URL`,
`MISSION_CONTROL_SESSION_SECRET`, `FOUNDER_PASSWORD`, `FOUNDER_EMAIL`,
`OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `GITHUB_TOKEN`, etc.) are attached to the
Cloud Run service directly (via `gcloud run services update --set-secrets` or
the console) — **not** by `platform-deploy.yml`'s `gcloud run deploy` step,
which only sets `SOURCE_BRANCH`/`SOURCE_COMMIT_SHA`/`SOURCE_COMMIT_TIMESTAMP`/
`GCP_PROJECT_ID`/`GCP_REGION`.

This works today because `gcloud run deploy` merges into the existing revision
spec rather than replacing it, so secrets attached out-of-band survive across
ordinary deploys. **This is fragile and easy to break silently**: any future
change that switches to a full-replace deploy method, or adds `--clear-secrets`
/ an explicit `--update-secrets`/`--remove-secrets` that omits one of the
existing bindings, will drop that secret from the service with no warning —
the container will still start and `/health` will still return 200 (see
`app/platform/persistence/readiness.py`'s silent SQLite fallback), so the
break can go unnoticed. Before changing the `deploy` job's `gcloud run deploy`
command, confirm the current bindings with:

```bash
gcloud run services describe ai-software-factory-production \
  --region=asia-southeast1 --project=ai-software-factory-500910 \
  --format="yaml(spec.template.spec.containers[0].env, spec.template.spec.containers[0].envFrom)"
```

## Principles

- GitHub OIDC ready.
- No long-lived cloud keys committed to the repository.

## Validation

```bash
python -m app.platform.gcp.check
```
