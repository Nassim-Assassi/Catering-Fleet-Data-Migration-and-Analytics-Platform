# Report Generator resources: ECR, Lambda, CloudWatch, IAM

resource "aws_ecr_repository" "report_generator_ecr" {
  name                 = "${var.INFRASTRUCTURE_NAME}-report-generator-ecr"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}



resource "aws_cloudwatch_log_group" "report_generator" {
  name              = "/lambda/${var.INFRASTRUCTURE_NAME}-report-generator"
  retention_in_days = 14
}

resource "aws_iam_role" "report_generator_role" {
  name = "${var.INFRASTRUCTURE_NAME}-report-generator-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# Allow Lambda to write logs to CloudWatch
resource "aws_iam_role_policy_attachment" "report_generator_logs" {
  role       = aws_iam_role.report_generator_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# S3 access for writing reports
resource "aws_iam_role_policy_attachment" "report_generator_s3" {
  role       = aws_iam_role.report_generator_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

# Athena access for querying
resource "aws_iam_role_policy_attachment" "report_generator_athena" {
  role       = aws_iam_role.report_generator_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonAthenaFullAccess"
}

# Glue access for database catalog
resource "aws_iam_role_policy_attachment" "report_generator_glue" {
  role       = aws_iam_role.report_generator_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# Secrets Manager access for credentials
resource "aws_iam_role_policy" "report_generator_secrets" {
  name = "${var.INFRASTRUCTURE_NAME}-report-generator-secrets-policy"
  role = aws_iam_role.report_generator_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          "arn:aws:secretsmanager:${var.AWS_REGION}:${data.aws_caller_identity.current.account_id}:secret:${var.INFRASTRUCTURE_NAME}-*"
        ]
      }
    ]
  })
}

resource "aws_lambda_function" "report_generator" {
  count               = local.deploy_report_lambda ? 1 : 0
  function_name       = "${var.INFRASTRUCTURE_NAME}-report-generator"
  role                = aws_iam_role.report_generator_role.arn
  timeout             = 300
  memory_size         = 512
  image_uri           = "${aws_ecr_repository.report_generator_ecr.repository_url}:latest"
  package_type        = "Image"

  environment {
    variables = {
      GLUE_DB_NAME   = aws_glue_catalog_database.glue_database.name
      S3_BUCKET_NAME = aws_s3_bucket.s3_bucket.bucket
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.report_generator_logs,
    aws_iam_role_policy_attachment.report_generator_s3,
    aws_iam_role_policy_attachment.report_generator_athena,
    aws_iam_role_policy_attachment.report_generator_glue,
    aws_iam_role_policy.report_generator_secrets,
    aws_cloudwatch_log_group.report_generator
  ]
}
