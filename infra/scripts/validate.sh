#!/usr/bin/env bash
set -euo pipefail

python -m app.platform.gcp.check

if command -v terraform >/dev/null 2>&1; then
  terraform fmt -check -recursive infra/terraform
else
  echo "terraform not installed; skipping terraform fmt"
fi
