# Production Gates

P1.9 defines the minimum repository checks required before live deployment.

## Gate command

```bash
python -m app.platform.gcp.check
python -m app.platform.gcp.ops_check
python -m app.platform.gcp.readiness
```

## Coverage

- Infrastructure foundation exists
- Environment roots are present
- Required Terraform modules are present
- Deployment scripts are present
- Observability validation exists
- Readiness validation exists

Cloud project-specific checks are added once the GCP project ID and deployment environment are configured.
