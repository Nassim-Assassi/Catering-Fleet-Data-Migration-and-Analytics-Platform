# Pipeline resources: ECR, CloudWatch, IAM, security group, ECS task definition and EventBridge scheduler

resource "aws_ecr_repository" "pipeline_ecr" {
  name                 = "${var.INFRASTRUCTURE_NAME}-pipeline-ecr"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_cloudwatch_log_group" "pipeline" {
  name              = "/ecs/${var.INFRASTRUCTURE_NAME}-pipeline"
  retention_in_days = 14
}

resource "aws_iam_role" "pipeline_task_role" {
  name = "${var.INFRASTRUCTURE_NAME}-pipeline-task-role"
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

resource "aws_iam_role_policy_attachment" "pipeline_athena_policy" {
  role       = aws_iam_role.pipeline_task_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonAthenaFullAccess"
}

resource "aws_iam_role_policy_attachment" "pipeline_s3_policy" {
  role       = aws_iam_role.pipeline_task_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

resource "aws_iam_role_policy_attachment" "pipeline_glue_policy" {
  role       = aws_iam_role.pipeline_task_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_security_group" "pipeline" {
  name        = "${var.INFRASTRUCTURE_NAME}-pipeline-sg"
  description = "Security group for scheduled pipeline task"
  vpc_id      = var.vpc_id

  ingress {
    from_port = 443
    to_port   = 443
    protocol  = "tcp"
    self      = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_ecs_task_definition" "pipeline" {
  family                   = "${var.INFRASTRUCTURE_NAME}-pipeline"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.pipeline_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "pipeline"
      image     = "${aws_ecr_repository.pipeline_ecr.repository_url}:latest"
      essential = true
      secrets = [
        {
          name      = "DB_HOST"
          valueFrom = "${aws_secretsmanager_secret.secrets.arn}:DB_HOST::"
        },
        {
          name      = "DB_PORT"
          valueFrom = "${aws_secretsmanager_secret.secrets.arn}:DB_PORT::"
        },
        {
          name      = "DB_NAME"
          valueFrom = "${aws_secretsmanager_secret.secrets.arn}:DB_NAME::"
        },
        {
          name      = "DB_USER"
          valueFrom = "${aws_secretsmanager_secret.secrets.arn}:DB_USER::"
        },
        {
          name      = "DB_PASSWORD"
          valueFrom = "${aws_secretsmanager_secret.secrets.arn}:DB_PASSWORD::"
        },
        {
          name      = "GLUE_DB_NAME"
          valueFrom = "${aws_secretsmanager_secret.secrets.arn}:GLUE_DB_NAME::"
        },
        {
          name      = "S3_BUCKET_NAME"
          valueFrom = "${aws_secretsmanager_secret.secrets.arn}:S3_BUCKET_NAME::"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.pipeline.name
          awslogs-region        = var.AWS_REGION
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])
}

resource "aws_iam_role" "eventbridge_scheduler_role" {
  name = "${var.INFRASTRUCTURE_NAME}-eventbridge-scheduler-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "scheduler.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "eventbridge_scheduler_policy" {
  name = "${var.INFRASTRUCTURE_NAME}-eventbridge-scheduler-policy"
  role = aws_iam_role.eventbridge_scheduler_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecs:RunTask"
        ]
        Resource = [
          aws_ecs_task_definition.pipeline.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = [
          aws_iam_role.ecs_task_execution_role.arn,
          aws_iam_role.pipeline_task_role.arn
        ]
      }
    ]
  })
}

resource "aws_vpc_endpoint" "secrets_manager" {
  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.AWS_REGION}.secretsmanager"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [var.private_subnet_id]
  security_group_ids  = [aws_security_group.pipeline.id]
  private_dns_enabled = true
}

resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.AWS_REGION}.ecr.api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [var.private_subnet_id]
  security_group_ids  = [aws_security_group.pipeline.id]
  private_dns_enabled = true
}

resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.AWS_REGION}.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [var.private_subnet_id]
  security_group_ids  = [aws_security_group.pipeline.id]
  private_dns_enabled = true
}

resource "aws_vpc_endpoint" "cloudwatch_logs" {
  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.AWS_REGION}.logs"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [var.private_subnet_id]
  security_group_ids  = [aws_security_group.pipeline.id]
  private_dns_enabled = true
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = var.vpc_id
  service_name      = "com.amazonaws.${var.AWS_REGION}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [var.private_route_table_id]
}

resource "aws_scheduler_schedule" "pipeline" {
  name                         = "${var.INFRASTRUCTURE_NAME}-pipeline-schedule"
  group_name                   = "default"
  schedule_expression          = "cron(15 9-18/3 ? * MON-FRI *)"
  schedule_expression_timezone = "Europe/London"
  state                        = "ENABLED"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = var.ecs_cluster_arn
    role_arn = aws_iam_role.eventbridge_scheduler_role.arn

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 2
    }

    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.pipeline.arn
      launch_type         = "FARGATE"
      platform_version    = "LATEST"
      task_count          = 1

      network_configuration {
        assign_public_ip = false
        subnets          = [var.private_subnet_id]
        security_groups  = [aws_security_group.pipeline.id]
      }
    }
  }
}
