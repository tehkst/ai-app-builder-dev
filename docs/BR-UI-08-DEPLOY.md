# BR-UI-08 Deploy Note

After merge:

1. Run Platform Deploy from GitHub Actions.
2. List Cloud Run revisions.
3. Move traffic to the newest revision.
4. Hard refresh Mission Control.
5. Validate Board Room visual behavior.

Rollback is a Cloud Run traffic switch to the previous known-good revision.
