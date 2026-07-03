#!/bin/bash

# Build and push report generator Docker image to ECR

set -e

# Get account ID and region from Terraform variables
cd "$(dirname "$0")/.."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(grep 'AWS_REGION' terraform/terraform.tfvars | grep -oE '"[^"]*"' | tr -d '"')
INFRASTRUCTURE_NAME=$(grep 'INFRASTRUCTURE_NAME' terraform/terraform.tfvars | grep -oE '"[^"]*"' | tr -d '"')

ECR_REGISTRY="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
ECR_REPO_NAME="${INFRASTRUCTURE_NAME}-report-generator-ecr"
IMAGE_URI="${ECR_REGISTRY}/${ECR_REPO_NAME}:latest"

echo "Building and pushing report generator image..."
echo "Registry: ${ECR_REGISTRY}"
echo "Repository: ${ECR_REPO_NAME}"
echo "Image URI: ${IMAGE_URI}"

# Login to ECR
echo "Logging in to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}

# Build the image for x86_64 (required for Lambda)
# Lambda requires Docker media type manifests, not OCI - disable provenance/sbom
# attestations and oci-mediatypes which buildx adds by default.
echo "Building Docker image for x86_64 architecture..."
cd report
docker buildx build \
  --platform linux/x86_64 \
  --provenance=false \
  --sbom=false \
  --output type=image,oci-mediatypes=false,push=true \
  -t ${IMAGE_URI} .

echo "Successfully pushed ${IMAGE_URI}"
