# V87 — End-to-End MVP Launch Smoke

V87 is the final approved private MVP launch-readiness milestone.

It aggregates the completed safety and readiness layers from V81 through V86 into a single final smoke check.

## Goal

Confirm the repository is ready for a private hosted MVP launch workflow after the deployment pack is merged.

## Included Readiness Areas

- V81 production config and healthcheck readiness
- V84 background job runner readiness
- V85 hosted sandbox boundary contract
- V86 Railway/Gcore deployment pack completeness

## Safety Boundary

V87 is a launch-readiness smoke only.

It must not:

- deploy to Railway
- deploy to Gcore
- build Docker images
- start Docker containers
- start Kubernetes workloads
- create public URLs
- provision databases
- write secrets
- start runtime servers
- start preview servers
- execute generated code
- bypass approval gates
- apply repairs
- restore files
- roll out generated modules

## Expected Result

Run:

```bash
python -m app.platform.agents.end_to_end_mvp_launch_smoke_check
```

Expected output includes:

```text
'passed': True
```

## Next Operational Step After V87

After V87 is merged, the codebase is ready for a manually approved private MVP deployment setup using the V86 deployment pack.

The recommended order is:

1. Connect Railway to GitHub.
2. Deploy from `main`.
3. Attach PostgreSQL.
4. Set production secrets from `.env.example`.
5. Keep `HOSTED_SANDBOX_PROVIDER=local_only`.
6. Visit `/health`.
7. Run production config readiness checks.
8. Perform a controlled private MVP review.

No cloud deployment is performed by V87 itself.
