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

variable "private_route_table_id" {
  type        = string
  description = "Private route table ID for S3 gateway endpoint."
}


