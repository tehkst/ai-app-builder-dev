# Deployment Workflow Foundation

P2.0.3 extends the deploy workflow with automated Cloud Run deployment and live health verification.

## Current behavior

The workflow can be triggered manually from GitHub Actions and supports environment selection.

It performs:

- Platform validation gates
- Cloud authentication when identity variables are configured
- Terraform format check
- Terraform local init by default
- Optional remote backend init
- Terraform validate
- Terraform plan when project variables are configured
- Optional Terraform apply when explicitly requested
- Docker image build
- Optional registry authentication
- Optional image publishing when image prefix is configured
- Optional Cloud Run deployment when explicitly requested
- Live health verification for `/health`, `/ready`, `/mission-control/health`, and `/mission-control/version`
- Deployment summary generation

## Required GitHub environment variables for live operations

- `GCP_PROJECT_ID`
- `GCP_REGION`
- `GCP_RUNTIME_SERVICE_ACCOUNT`
- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_DEPLOY_SERVICE_ACCOUNT`
- `GCP_REGISTRY_HOST`
- `CONTAINER_IMAGE_PREFIX`
- `TF_STATE_BUCKET`

## Safety

- Publishing is disabled by default
- Service deployment is disabled by default
- Infrastructure apply is disabled by default
- Remote backend usage is disabled by default
- Authentication runs only when identity variables are configured
- Image publishing fails fast if the image prefix is missing
- Service deployment requires image publishing and configured GCP variables
- Terraform plan/apply is skipped unless the project ID is configured

## Deployment mode

To publish and deploy the current branch to Cloud Run, run the workflow with:

- `publish_image=true`
- `deploy_service=true`
- `apply_infra=false`
- `use_remote_backend=true`

## Next steps

Later PRs will add:

- Release metadata
- Rollback support
- Deployment history in Launch Center
