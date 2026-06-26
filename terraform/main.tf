terraform {
  required_providers {
    aws   = { source = "hashicorp/aws" }
    local = { source = "hashicorp/local" }
  }
}

provider "aws" {
  region     = var.AWS_REGION
  access_key = var.AWS_ACCESS_KEY_ID
  secret_key = var.AWS_SECRET_ACCESS_KEY
}

locals {
  repo_root = abspath("${path.root}/..")
}

# S3 bucket for storing data
resource "aws_s3_bucket" "s3_bucket" {
  bucket        = "${var.INFRASTRUCTURE_NAME}-bucket"
  force_destroy = true
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
        Resource = "arn:aws:s3:::${aws_s3_bucket.s3_bucket.bucket}/*"
      }
    ]
  })
}


resource "aws_glue_crawler" "glue_crawler" {
  name          = "${var.INFRASTRUCTURE_NAME}-glue-crawler"
  database_name = aws_glue_catalog_database.glue_database.name
  role          = aws_iam_role.glue_service_role.arn
  s3_target {
    path = "s3://${aws_s3_bucket.s3_bucket.bucket}/"
  }
}

# Generate a .env file with sensitive information
resource "local_sensitive_file" "infrastructure_env_file" {
  filename = "${local.repo_root}/.env"
  content = templatefile("${local.repo_root}/env_template", {
    db_host        = var.DB_HOST
    db_port        = var.DB_PORT
    db_name        = var.DB_NAME
    db_user        = var.DB_USER
    db_password    = var.DB_PASSWORD
    s3_bucket_name = aws_s3_bucket.s3_bucket.bucket
    aws_access_key_id = var.AWS_ACCESS_KEY_ID
    aws_secret_access_key = var.AWS_SECRET_ACCESS_KEY
    aws_region = var.AWS_REGION
    glue_db_name = aws_glue_catalog_database.glue_database.name
  })
  file_permission = "0600"
}