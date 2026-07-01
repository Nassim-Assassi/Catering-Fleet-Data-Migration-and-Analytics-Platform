# AWS Secrets Manager for storing sensitive credentials

resource "aws_secretsmanager_secret" "secrets" {
  name                    = "${var.INFRASTRUCTURE_NAME}-secrets"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.secrets.id
  secret_string = jsonencode({
    DB_HOST        = var.DB_HOST
    DB_PORT        = var.DB_PORT
    DB_NAME        = var.DB_NAME
    DB_USER        = var.DB_USER
    DB_PASSWORD    = var.DB_PASSWORD
    GLUE_DB_NAME   = aws_glue_catalog_database.glue_database.name
    S3_BUCKET_NAME = aws_s3_bucket.s3_bucket.bucket
  })
}

# Grant ECS task execution role permission to read secrets
resource "aws_iam_role_policy" "ecs_task_execution_secrets_policy" {
  name = "${var.INFRASTRUCTURE_NAME}-ecs-task-execution-secrets-policy"
  role = aws_iam_role.ecs_task_execution_role.id

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
