# ai-app-builder-dev

AI Software Factory development repository.

## Standard Validation

Run the platform source validation suite before committing or pushing changes:

```bash
python3 -m app.platform.validate_all --profile local
```

Expected success output:

```text
"passed": true
VALIDATION PASSED
```

The platform profile runs deterministic source, architecture, governance,
runtime, authentication, and deployment-contract checks. Generated application
and live provider checks use explicit profiles:

```bash
python3 -m app.platform.validate_all --profile artifact
python3 -m app.platform.validate_all --profile ai-integration
```

See `docs/release/VALIDATION_ARCHITECTURE.md` for applicability, dependency,
secret, cloud, smoke, regression, and release-gate classifications.

## Security Report

To view the generated app security posture directly:

```bash
python3 -m app.platform.security_report
```

Expected success output:

```text
"overall": "MVP-safe"
"passed": true
```

## Generated App Security Baseline

The current generated app baseline includes:

```text
Platform internal API auth
Platform audit logs
Platform rate limiting
Platform rate-limit audit logs
Generated app auth rate limiting
Generated membership-based RBAC
Generated audit logging
Generated frontend safe error handling
Generated frontend auth/token helpers
Generated frontend page enforcement
Default organization + owner membership on registration
Protected generated routes using RBAC
RBAC denial audit detail
Frontend contract validation
Optional frontend build validation
Generated app security report
Unified validation command
```

## Local Development Notes

Use the project virtual environment before running Python commands:

```bash
source /Users/toniteh/venv/bin/activate
```

When a GitHub change is committed directly through the assistant, sync your local repository:

```bash
git pull origin main
```
