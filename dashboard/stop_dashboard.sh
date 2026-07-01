#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}. Run terraform apply first to generate it." >&2
  exit 1
fi

set -a
source "${ENV_FILE}"
set +a

: "${AWS_REGION:?AWS_REGION is required in .env}"
: "${ECS_CLUSTER_ARN:?ECS_CLUSTER_ARN is required in .env}"
: "${DASHBOARD_ECS_SERVICE_NAME:?DASHBOARD_ECS_SERVICE_NAME is required in .env}"

echo "Scaling ECS service '${DASHBOARD_ECS_SERVICE_NAME}' to 0..."
aws ecs update-service \
  --region "${AWS_REGION}" \
  --cluster "${ECS_CLUSTER_ARN}" \
  --service "${DASHBOARD_ECS_SERVICE_NAME}" \
  --desired-count 0 >/dev/null

echo "Waiting for ECS service to become stable..."
aws ecs wait services-stable \
  --region "${AWS_REGION}" \
  --cluster "${ECS_CLUSTER_ARN}" \
  --services "${DASHBOARD_ECS_SERVICE_NAME}"

echo "Dashboard stopped."
