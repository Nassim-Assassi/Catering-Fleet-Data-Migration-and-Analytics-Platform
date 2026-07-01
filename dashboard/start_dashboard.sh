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
: "${DASHBOARD_IMAGE_URI:?DASHBOARD_IMAGE_URI is required in .env}"
: "${ECR_REGISTRY:?ECR_REGISTRY is required in .env}"

echo "Logging into ECR registry '${ECR_REGISTRY}'..."
aws ecr get-login-password --region "${AWS_REGION}" \
  | docker login --username AWS --password-stdin "${ECR_REGISTRY}"

echo "Building dashboard image '${DASHBOARD_IMAGE_URI}'..."
docker build --platform=linux/amd64 -f "${SCRIPT_DIR}/dockerfile" -t "${DASHBOARD_IMAGE_URI}" "${SCRIPT_DIR}"

echo "Pushing dashboard image to ECR..."
docker push "${DASHBOARD_IMAGE_URI}"

echo "Scaling ECS service '${DASHBOARD_ECS_SERVICE_NAME}' to 1..."
aws ecs update-service \
  --region "${AWS_REGION}" \
  --cluster "${ECS_CLUSTER_ARN}" \
  --service "${DASHBOARD_ECS_SERVICE_NAME}" \
  --desired-count 1 >/dev/null

echo "Forcing new deployment so ECS pulls latest image..."
aws ecs update-service \
  --region "${AWS_REGION}" \
  --cluster "${ECS_CLUSTER_ARN}" \
  --service "${DASHBOARD_ECS_SERVICE_NAME}" \
  --force-new-deployment >/dev/null

echo "Waiting for ECS service to become stable..."
aws ecs wait services-stable \
  --region "${AWS_REGION}" \
  --cluster "${ECS_CLUSTER_ARN}" \
  --services "${DASHBOARD_ECS_SERVICE_NAME}"

echo "Dashboard image pushed and ECS service is running."
