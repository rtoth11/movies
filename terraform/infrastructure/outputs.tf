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

output "alb_url" {
  description = "The URL of the Application Load Balancer for the frontend service."
  value       = try(aws_lb.movies_alb[0].dns_name, null)
}

output "backend_instance_id" {
  description = "The ID of the backend EC2 instance"
  value       = try(aws_instance.backend[0].id, null)
}

output "frontend_instance_id" {
  description = "The ID of the frontend EC2 instance"
  value       = try(aws_instance.frontend[0].id, null)
}

output "backend_log_group" {
  description = "The name of the backend CloudWatch log group"
  value       = try(aws_cloudwatch_log_group.backend_log_group[0].name, null)
}

output "frontend_log_group" {
  description = "The name of the frontend CloudWatch log group"
  value       = try(aws_cloudwatch_log_group.frontend_log_group[0].name, null)
}

output "aws_region" {
  description = "The AWS region where the infrastructure is deployed"
  value       = var.region
}
