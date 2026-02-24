output "extraction_ecr_repository_url" {
  description = "The URL of the ECR repository that stores the extraction image."
  value       = aws_ecr_repository.extraction_ecr_repository.repository_url
}

output "backend_ecr_repository_url" {
  description = "The URL of the ECR repository that stores the backend image."
  value       = aws_ecrpublic_repository.backend_ecr_repository.repository_uri
}

output "frontend_ecr_repository_url" {
  description = "The URL of the ECR repository that stores the frontend image."
  value       = aws_ecrpublic_repository.frontend_ecr_repository.repository_uri
}

output "role_for_infrastructure_update" {
  description = "The ARN of the IAM role that can be assumed to update the infrastructure."
  value       = aws_iam_role.role_for_infrastructure_update.arn
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
  value       = try(aws_lb.movies_alb[0].dns_name, null)
}

output "ecs_cluster_name" {
  description = "The name of the ECS cluster that contains the backend and frontend tasks."
  value       = try(aws_ecs_cluster.movies_cluster[0].name, null)
}

output "backend_ecs_task_definition_family" {
  description = "The family of the backend ECS task definition."
  value       = try(aws_ecs_task_definition.backend[0].family, null)
}

output "frontend_ecs_task_definition_family" {
  description = "The family of the frontend ECS task definition."
  value       = try(aws_ecs_task_definition.frontend[0].family, null)
}

output "backend_ecs_service_name" {
  description = "The name of the backend ECS service."
  value       = try(aws_ecs_service.backend[0].name, null)
}

output "frontend_ecs_service_name" {
  description = "The name of the frontend ECS service."
  value       = try(aws_ecs_service.frontend[0].name, null)
}
