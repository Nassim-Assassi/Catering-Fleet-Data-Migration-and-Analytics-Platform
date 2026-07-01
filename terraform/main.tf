# General resources: Terraform configuration, provider, locals, shared data sources and IAM

terraform {
  required_providers {
    aws   = { source = "hashicorp/aws" }
    local = { source = "hashicorp/local" }
    http  = { source = "hashicorp/http" }
  }
}

provider "aws" {
  region = var.AWS_REGION
}

data "aws_caller_identity" "current" {}

# Fetch public IP for dashboard security group
data "http" "public_ip" {
  url = "https://checkip.amazonaws.com"
}

locals {
  repo_root                  = abspath("${path.root}/..")
  fact_projection_year_start = 2026
  fact_projection_year_end   = tonumber(formatdate("YYYY", timestamp())) + 1
  my_public_ip               = chomp(data.http.public_ip.response_body)
}

# Shared ECS task execution role used by all ECS tasks
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "${var.INFRASTRUCTURE_NAME}-ecs-task-execution-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}
