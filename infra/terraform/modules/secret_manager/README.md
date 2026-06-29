# Secret Manager Module

Reusable Secret Manager module for runtime configuration and sensitive application inputs.

## Features

- Creates named Secret Manager secrets
- Uses automatic replication
- Applies common labels
- Grants runtime service accounts read access
- Does not create secret versions or commit secret payloads

Secret values are inserted out-of-band during deployment or operations workflows.
