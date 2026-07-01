# Dashboard resources: ECR, CloudWatch, IAM, security group, ECS task definition and service

resource "aws_ecr_repository" "dashboard_ecr" {
  name                 = "${var.INFRASTRUCTURE_NAME}-dashboard-ecr"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_cloudwatch_log_group" "dashboard" {
  name              = "/ecs/${var.INFRASTRUCTURE_NAME}-dashboard"
  retention_in_days = 14
}

resource "aws_iam_role" "dashboard_task_role" {
  name = "${var.INFRASTRUCTURE_NAME}-dashboard-task-role"
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

resource "aws_iam_role_policy_attachment" "dashboard_athena_policy" {
  role       = aws_iam_role.dashboard_task_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonAthenaFullAccess"
}

resource "aws_iam_role_policy_attachment" "dashboard_s3_policy" {
  role       = aws_iam_role.dashboard_task_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

resource "aws_iam_role_policy_attachment" "dashboard_glue_policy" {
  role       = aws_iam_role.dashboard_task_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_security_group" "dashboard" {
  name        = "${var.INFRASTRUCTURE_NAME}-dashboard-sg"
  description = "Allow dashboard access on port 8501"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = ["${local.my_public_ip}/32"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_ecs_task_definition" "dashboard" {
  family                   = "${var.INFRASTRUCTURE_NAME}-dashboard"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.dashboard_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "dashboard"
      image     = "${aws_ecr_repository.dashboard_ecr.repository_url}:latest"
      essential = true
      portMappings = [
        {
          containerPort = 8501
          hostPort      = 8501
          protocol      = "tcp"
        }
      ]
      environment = []
      secrets = [
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
          awslogs-group         = aws_cloudwatch_log_group.dashboard.name
          awslogs-region        = var.AWS_REGION
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "dashboard" {
  name            = "${var.INFRASTRUCTURE_NAME}-dashboard"
  cluster         = var.ecs_cluster_arn
  task_definition = aws_ecs_task_definition.dashboard.arn
  launch_type     = "FARGATE"
  desired_count   = 0

  network_configuration {
    subnets          = [var.public_subnet_id]
    security_groups  = [aws_security_group.dashboard.id]
    assign_public_ip = true
  }

  timeouts {
    delete = "5m"
  }
}
