# BR-UI-08 Rollback

If the Board Room UI regresses after deployment, roll traffic back to the previous known-good Cloud Run revision before this PR.

This PR is isolated to the Board Room UI renderer and documentation notes, so rollback should not require database or infrastructure actions.
