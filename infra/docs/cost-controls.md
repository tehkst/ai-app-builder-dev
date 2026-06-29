# Cost Controls

AI Software Factory requires cost visibility before live infrastructure changes.

## Required controls

- Terraform plan before apply
- Infracost estimate before apply
- Manual approval before apply
- Google Cloud Budget alerts before production rollout

## Recommended initial budget

Set an initial monthly budget of USD 100 for the production project.

Recommended alert thresholds:

- 50 percent
- 80 percent
- 100 percent

## Lean MVP target

The first live deployment should remain lean:

- Cloud Run with scale-to-zero where possible
- Small Cloud SQL PostgreSQL instance
- Artifact Registry
- Secret Manager
- Cloud Storage state bucket
- Logging and Monitoring

Avoid Redis, NAT gateways, always-on workers, and load balancers until required.

## Infracost

When `INFRACOST_API_KEY` is configured, the deployment workflow can generate cost estimates from the Terraform plan before apply.

`MAX_MONTHLY_COST_USD` defines the initial allowed monthly cost ceiling.
