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
