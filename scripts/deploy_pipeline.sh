#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PIPELINE_DIR="${REPO_ROOT}/pipeline"
ENV_FILE="${REPO_ROOT}/.env"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}. Run terraform apply first to generate it." >&2
  exit 1
fi

set -a
source "${ENV_FILE}"
set +a

: "${AWS_REGION:?AWS_REGION is required in .env}"
: "${IMAGE_URI:?IMAGE_URI is required in .env}"
: "${ECR_REGISTRY:?ECR_REGISTRY is required in .env}"
echo "Logging into ECR registry '${ECR_REGISTRY}'..."
aws ecr get-login-password --region "${AWS_REGION}" \
  | docker login --username AWS --password-stdin "${ECR_REGISTRY}"

echo "Building pipeline image '${IMAGE_URI}'..."
docker build --platform=linux/amd64 -f "${PIPELINE_DIR}/dockerfile" -t "${IMAGE_URI}" "${PIPELINE_DIR}"

echo "Pushing pipeline image to ECR..."
docker push "${IMAGE_URI}"

echo "✓ Pipeline image deployed successfully!"
echo "✓ The EventBridge scheduler will automatically run the pipeline task on schedule:"
echo "  - Cron: cron(15 9-18/3 ? * MON-FRI *)"
echo "  - Times: 09:15, 12:15, 15:15, 18:15 UK time (Europe/London)"
echo "  - Days: Monday-Friday"
