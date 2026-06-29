#!/usr/bin/env bash
set -euo pipefail

python -m app.platform.gcp.check
python -m app.platform.gcp.ops_check
python -m app.platform.gcp.readiness
