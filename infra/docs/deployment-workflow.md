# Deployment Workflow Foundation

P2.0.3 extends the deploy workflow with automated Cloud Run deployment and live health verification.

## Current behavior

The workflow can be triggered manually from GitHub Actions and supports environment selection.

It performs:

- Platform validation gates
- Cloud authentication when identity variables are configured
- Docker image build
- Optional registry authentication
- Optional image publishing when image prefix is configured
- Optional Cloud Run deployment when explicitly requested
- Live health verification for `/health`, `/ready`, `/mission-control/health`, and `/mission-control/version`
  (authenticated with an identity token for non-production environments, which
  stay private)
- Deployment summary generation

Cloud Run, Cloud SQL, Secret Manager, and Artifact Registry resources
themselves are provisioned directly in the GCP project (not by this
workflow); the workflow only builds/publishes the image and updates the
Cloud Run service revision.

## Required GitHub environment variables for live operations

- `GCP_PROJECT_ID`
- `GCP_REGION`
- `GCP_RUNTIME_SERVICE_ACCOUNT`
- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_DEPLOY_SERVICE_ACCOUNT`
- `GCP_REGISTRY_HOST`
- `CONTAINER_IMAGE_PREFIX`

## Safety

- Publishing is disabled by default
- Service deployment is disabled by default
- Authentication runs only when identity variables are configured
- Image publishing fails fast if the image prefix is missing
- Service deployment requires image publishing and configured GCP variables

## Deployment mode

To publish and deploy the current branch to Cloud Run, run the workflow with:

- `publish_image=true`
- `deploy_service=true`

## Next steps

Later PRs will add:

- Release metadata
- Rollback support
- Deployment history in Launch Center
