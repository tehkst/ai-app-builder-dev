# Deployment Workflow Foundation

P1.10.3 extends the deploy workflow with cloud authentication and remote backend controls.

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
- Deployment summary generation

## Required GitHub environment variables for live operations

- `GCP_PROJECT_ID`
- `GCP_RUNTIME_SERVICE_ACCOUNT`
- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_DEPLOY_SERVICE_ACCOUNT`
- `GCP_REGISTRY_HOST`
- `CONTAINER_IMAGE_PREFIX`
- `TF_STATE_BUCKET`

## Safety

- Publishing is disabled by default
- Infrastructure apply is disabled by default
- Remote backend usage is disabled by default
- Authentication runs only when identity variables are configured
- Image publishing fails fast if the image prefix is missing
- Terraform plan/apply is skipped unless the project ID is configured

## Next steps

Later P1.10 PRs will add:

- Release metadata
- Rollback support
- Deployment verification
