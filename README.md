# ai-app-builder-dev

AI Software Factory development repository.

## Standard Validation

Run the full validation suite before committing or pushing changes:

```bash
python3 -m app.platform.validate_all
```

Expected success output:

```text
"passed": true
VALIDATION PASSED
```

The unified validation command runs:

```text
compatibility_scanner
dependency_policy
platform_routes
frontend_contract
frontend_build
security_report
generation_graph
```

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
