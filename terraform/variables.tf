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

variable "AWS_ACCESS_KEY_ID" {
  type        = string
  sensitive   = true
  description = "The AWS access key ID."
}

variable "AWS_SECRET_ACCESS_KEY" {
  type        = string
  sensitive   = true
  description = "The AWS secret access key."
}