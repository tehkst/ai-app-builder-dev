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

## Principles

- GitHub OIDC ready.
- No long-lived cloud keys committed to the repository.

## Validation

```bash
python -m app.platform.gcp.check
```
