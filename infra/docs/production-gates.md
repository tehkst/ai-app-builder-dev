# Production Gates

P1.9 defines the minimum repository checks required before live deployment.

## Gate command

```bash
python -m app.platform.gcp.check
python -m app.platform.gcp.readiness
bash infra/scripts/gate.sh
```

## Coverage

- Deployment foundation (Dockerfile, deploy workflow) exists
- Deploy workflow defines the Cloud Run deploy and health-check steps
- Readiness validation exists

Cloud project-specific checks are added once the GCP project ID and deployment environment are configured.
