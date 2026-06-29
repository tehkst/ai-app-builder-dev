# Bootstrap

Bootstrap prepares the cloud project for Terraform-managed production infrastructure.

## Required inputs

- GCP project ID
- Default region
- Terraform state bucket name
- GitHub organization/repository
- Deployment service account names

## Target outcome

- Remote state bucket created outside normal environment roots.
- State access restricted to deployment operators and GitHub OIDC service accounts.
- Production infrastructure remains reproducible from Terraform roots.

Actual cloud provisioning requires authenticated GCP access and will be wired during the GitHub OIDC milestone.
