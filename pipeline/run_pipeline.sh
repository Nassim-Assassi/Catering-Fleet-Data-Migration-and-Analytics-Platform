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
: "${PIPELINE_TASK_DEFINITION_ARN:?PIPELINE_TASK_DEFINITION_ARN is required in .env}"
: "${PIPELINE_SUBNET_ID:?PIPELINE_SUBNET_ID is required in .env}"
: "${PIPELINE_SECURITY_GROUP_ID:?PIPELINE_SECURITY_GROUP_ID is required in .env}"

echo "Running pipeline task..."
TASK_ARN=$(aws ecs run-task \
  --region "${AWS_REGION}" \
  --cluster "${ECS_CLUSTER_ARN}" \
  --task-definition "${PIPELINE_TASK_DEFINITION_ARN}" \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[${PIPELINE_SUBNET_ID}],securityGroups=[${PIPELINE_SECURITY_GROUP_ID}],assignPublicIp=DISABLED}" \
  --query 'tasks[0].taskArn' \
  --output text)

echo "✓ Pipeline task started: ${TASK_ARN}"
echo "Waiting for task to complete..."

aws ecs wait tasks-stopped \
  --region "${AWS_REGION}" \
  --cluster "${ECS_CLUSTER_ARN}" \
  --tasks "${TASK_ARN}"

# Get task exit code
EXIT_CODE=$(aws ecs describe-tasks \
  --region "${AWS_REGION}" \
  --cluster "${ECS_CLUSTER_ARN}" \
  --tasks "${TASK_ARN}" \
  --query 'tasks[0].containers[0].exitCode' \
  --output text)

if [[ "${EXIT_CODE}" == "0" ]]; then
  echo "✓ Pipeline task completed successfully (exit code: ${EXIT_CODE})"
else
  echo "✗ Pipeline task failed (exit code: ${EXIT_CODE})" >&2
  exit "${EXIT_CODE}"
fi
