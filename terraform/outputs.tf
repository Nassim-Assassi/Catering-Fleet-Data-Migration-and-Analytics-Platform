# Output resources: generates the .env file with non-sensitive infrastructure values
# Sensitive credentials (DB_*, AWS_*) are now stored in AWS Secrets Manager

resource "local_sensitive_file" "infrastructure_env_file" {
  filename = "${local.repo_root}/.env"
  content = templatefile("${local.repo_root}/env_template", {
    aws_region            = var.AWS_REGION
    infrastructure_name   = var.INFRASTRUCTURE_NAME
    ecs_cluster_arn       = var.ecs_cluster_arn
    dashboard_ecs_service_name = aws_ecs_service.dashboard.name
    dashboard_ecr_repository_url = aws_ecr_repository.dashboard_ecr.repository_url
    dashboard_image_uri   = "${aws_ecr_repository.dashboard_ecr.repository_url}:latest"
    pipeline_ecr_repository_url = aws_ecr_repository.pipeline_ecr.repository_url
    pipeline_task_definition_arn = aws_ecs_task_definition.pipeline.arn
    pipeline_subnet_id    = var.public_subnet_id
    pipeline_security_group_id = aws_security_group.pipeline.id
    image_uri             = "${aws_ecr_repository.pipeline_ecr.repository_url}:latest"
    ecr_registry          = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.AWS_REGION}.amazonaws.com"
  })
  file_permission = "0600"
}