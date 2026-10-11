variable "INFRASTRUCTURE_NAME" {
  type        = string
  sensitive   = true
  description = "The name of the infrastructure/project. Used for naming resources."
}

variable "AWS_REGION" {
  type        = string
  sensitive   = true
  description = "The AWS region where resources will be created."
}

variable "DB_HOST" {
  type        = string
  sensitive   = true
  description = "The hostname of the database."
}

variable "DB_PORT" {
  type        = string
  sensitive   = true
  description = "The port number of the database."
}

variable "DB_NAME" {
  type        = string
  sensitive   = true
  description = "The name of the database."
}

variable "DB_USER" {
  type        = string
  sensitive   = true
  description = "The username for the database."
}

variable "DB_PASSWORD" {
  type        = string
  sensitive   = true
  description = "The password for the database."
}

variable "ecs_cluster_arn" {
  type        = string
  description = "Existing ECS cluster ARN to deploy services and tasks into."
}

variable "vpc_id" {
  type        = string
  description = "VPC ID where ECS security groups will be created."
}

variable "public_subnet_id" {
  type        = string
  description = "Public subnet ID for internet-reachable ECS workloads."
}

variable "private_subnet_id" {
  type        = string
  description = "Private subnet ID for internal ECS workloads."
}

variable "deploy_report_generator_lambda" {
  type        = string
  description = <<-EOT
    Deploy the report generator Lambda function?
    Only set to 'yes' AFTER you have pushed the Docker image to ECR using: bash scripts/build_and_push.sh
    
    Valid values: yes, no
  EOT

  validation {
    condition     = contains(["yes", "no"], lower(var.deploy_report_generator_lambda))
    error_message = "Must be 'yes' or 'no'"
  }
}
