# V87 — End-to-End MVP Launch Smoke

V87 is the final approved private MVP launch-readiness milestone.

It aggregates the completed safety and readiness layers from V81 through V86 into a single final smoke check.

## Goal

Confirm the repository is ready for a private hosted MVP launch workflow after the deployment pack is merged.

## Included Readiness Areas

- V81 production config and healthcheck readiness
- V84 background job runner readiness
- V85 hosted sandbox boundary contract
- V86 deployment pack completeness

## Safety Boundary

V87 is a launch-readiness smoke only.

It must not:

- deploy to GCP Cloud Run
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

After V87 is merged, the codebase is ready for a manually approved private MVP deployment setup. The
platform's actual deployment target is GCP Cloud Run, not the Railway path originally described in the
V86 deployment pack.

The recommended order is:

1. Dispatch `.github/workflows/platform-deploy.yml` for the target environment.
2. Let the workflow's `validate` job run the GCP readiness/deploy-check gates and `infra/scripts/gate.sh`.
3. Let the `deploy` job build the image and run `gcloud run deploy` with secrets from GCP Secret Manager.
4. Keep `HOSTED_SANDBOX_PROVIDER=local_only`.
5. Visit `/health`.
6. Run production config readiness checks.
7. Perform a controlled private MVP review.

No cloud deployment is performed by V87 itself.
