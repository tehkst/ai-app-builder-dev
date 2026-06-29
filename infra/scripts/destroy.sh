#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT="${1:-dev}"
ROOT="infra/terraform/environments/${ENVIRONMENT}"

cd "${ROOT}"
terraform init
terraform destroy
