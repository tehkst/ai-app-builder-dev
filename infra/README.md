# Production Infrastructure

This directory contains the Google Cloud production infrastructure foundation for AI Software Factory.

## Structure

- `bootstrap/` prepares remote state and bootstrap guidance.
- `terraform/shared/` contains common provider, version, and variable definitions.
- `terraform/modules/` contains reusable production infrastructure modules.
- `terraform/environments/` contains isolated dev, staging, and production roots.
- `scripts/` contains operator entrypoints for validation, planning, and apply flows.

## Principles

- Infrastructure as Code first.
- Environment isolation by root module.
- Reusable modules for platform capabilities.
- GitHub OIDC ready.
- No long-lived cloud keys committed to the repository.

## Validation

```bash
python -m app.platform.gcp.check
```
