terraform {
  required_providers {
    aws   = { source = "hashicorp/aws" }
    local = { source = "hashicorp/local" }
  }
}

provider "aws" {
  region = var.AWS_REGION
}

locals {
  repo_root = abspath("${path.root}/..")
}

# S3 bucket for storing data
resource "aws_s3_bucket" "s3_bucket" {
  bucket = "${var.INFRASTRUCTURE_NAME}-bucket"
}

# Glue Catalog Database 
resource "aws_glue_catalog_database" "glue_database" {
  name = "${var.INFRASTRUCTURE_NAME}-glue-database"
}

# IAM role for the Glue service
resource "aws_iam_role" "glue_service_role" {
  name = "${var.INFRASTRUCTURE_NAME}-glue-service-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# Attach AWS-managed service role policy for Glue
resource "aws_iam_role_policy_attachment" "glue_service_role_managed" {
  role       = aws_iam_role.glue_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# Keep explicit S3 read access to this project's bucket/prefix
resource "aws_iam_role_policy" "glue_s3_access_policy" {
  name = "${var.INFRASTRUCTURE_NAME}-glue-s3-access-policy"
  role = aws_iam_role.glue_service_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetBucketLocation",
          "s3:ListBucket"
        ]
        Resource = "arn:aws:s3:::${aws_s3_bucket.s3_bucket.bucket}"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = "arn:aws:s3:::${aws_s3_bucket.s3_bucket.bucket}/data/*"
      }
    ]
  })
}


resource "aws_glue_crawler" "glue_crawler" {
  name          = "${var.INFRASTRUCTURE_NAME}-glue-crawler"
  database_name = aws_glue_catalog_database.glue_database.name
  role          = aws_iam_role.glue_service_role.arn
  s3_target {
    path = "s3://${aws_s3_bucket.s3_bucket.bucket}/data/"
  }
}