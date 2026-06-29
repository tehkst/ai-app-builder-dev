# D3.4 Data Safety Checklist

Status: ready for implementation governance
Scope: production data layer safety, verification, and operator readiness

## Snapshot cadence

- Define automated database snapshots for each managed environment.
- Keep tenant data isolated by environment, project, and database instance.
- Record snapshot schedule, owner, storage location, and last successful run.
- Treat snapshot configuration as infrastructure-owned and review it during release readiness.

## Retention policy

- Maintain separate retention windows for daily, weekly, and monthly recovery points.
- Align retention with customer contracts, regulatory obligations, and incident response needs.
- Document expiry behavior before customer data is deleted from retained storage.
- Require approval before reducing retention duration for production environments.

## Restore drill

- Run a scheduled restore drill into an isolated non-production environment.
- Verify application boot, migration compatibility, tenant isolation, and event replay assumptions.
- Capture recovery time, recovery point, validation result, operator, and follow-up actions.
- Block production promotion if the latest drill fails without an accepted mitigation.

## Ownership

- Assign primary and secondary owners for data safety operations.
- Define escalation contacts for infrastructure, database, application, and security review.
- Keep runbook ownership separate from feature ownership to preserve operational accountability.
- Review ownership at each major D-roadmap milestone.

## Verification

- Validate that recovery points exist before deployment approval.
- Validate that restored data passes migration, tenant, and event-record checks.
- Validate that restored environments do not expose customer traffic or production credentials.
- Keep evidence links with release notes and incident records.

## Incident notes

- Record incident timeline, scope, affected tenants, remediation, and customer impact.
- Preserve event records and operator actions required for post-incident analysis.
- Track permanent corrective actions as follow-up engineering work.
- Review incident notes before changing snapshot cadence or retention windows.

## D3.4 completion criteria

- Checklist committed in repository.
- Standalone validation confirms checklist sections exist.
- No runtime behavior is changed.
- No existing data-layer APIs are modified.
