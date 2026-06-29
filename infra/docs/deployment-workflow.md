# Deployment Workflow Foundation

P1.10.2 extends the deploy workflow with guarded publish and apply wiring.

## Current behavior

The workflow can be triggered manually from GitHub Actions and supports environment selection.

It performs:

- Platform validation gates
- Terraform format check
- Terraform init without remote backend
- Terraform validate
- Terraform plan when project variables are configured
- Optional Terraform apply when explicitly requested
- Docker image build
- Optional image publishing when image prefix is configured
- Deployment summary generation

## Required GitHub environment variables for live operations

- `GCP_PROJECT_ID`
- `GCP_RUNTIME_SERVICE_ACCOUNT`
- `CONTAINER_IMAGE_PREFIX`

## Safety

- Publishing is disabled by default
- Infrastructure apply is disabled by default
- Image publishing fails fast if the image prefix is missing
- Terraform plan/apply is skipped unless the project ID is configured

## Next steps

Later P1.10 PRs will add:

- Cloud authentication action wiring
- Remote backend initialization
- Release metadata
- Rollback support
