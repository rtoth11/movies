output "ingestion_ecr_repository_url" {
  description = "The URL of the ECR repository that stores the ingestion image."
  value       = aws_ecr_repository.ingestion_ecr_repository.repository_url
}

output "backend_ecr_repository_url" {
  description = "The URL of the ECR repository that stores the backend image."
  value       = aws_ecrpublic_repository.backend_ecr_repository.repository_uri
}

output "frontend_ecr_repository_url" {
  description = "The URL of the ECR repository that stores the frontend image."
  value       = aws_ecrpublic_repository.frontend_ecr_repository.repository_uri
}

output "github_actions_role_arn" {
  description = "The ARN of the IAM role that GitHub Actions can assume."
  value       = aws_iam_role.github_actions_role.arn
}

output "ingestion_lambda_function_name" {
  description = "The name of the ingestion Lambda function."
  value       = aws_lambda_function.ingestion_lambda.function_name
}

output "movies_s3_bucket_name" {
  description = "The name of the S3 bucket used for movie data storage."
  value       = aws_s3_bucket.movies_s3_bucket.bucket
}

output "pg_host" {
  description = "The address of the PostgreSQL RDS instance."
  value       = aws_db_instance.postgres_instance.address
  sensitive   = true
}

output "pg_port" {
  description = "The port of the PostgreSQL RDS instance."
  value       = aws_db_instance.postgres_instance.port
}

output "alb_url" {
  description = "The URL of the Application Load Balancer for the frontend service."
  value       = aws_lb.movies_alb.dns_name
}

output "ecs_cluster_name" {
  description = "The name of the ECS cluster that contains the backend and frontend tasks."
  value       = aws_ecs_cluster.movies_cluster.name
}

output "backend_ecs_task_definition_family" {
  description = "The family of the backend ECS task definition."
  value       = aws_ecs_task_definition.backend.family
}

output "frontend_ecs_task_definition_family" {
  description = "The family of the frontend ECS task definition."
  value       = aws_ecs_task_definition.frontend.family
}

output "backend_ecs_service_name" {
  description = "The name of the backend ECS service."
  value       = aws_ecs_service.backend.name
}

output "frontend_ecs_service_name" {
  description = "The name of the frontend ECS service."
  value       = aws_ecs_service.frontend.name
}
