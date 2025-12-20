output "ingestion_ecr_repository_url" {
  description = "The URL of the ECR repository that stores the ingestion image."
  value       = aws_ecr_repository.ingestion_ecr_repository.repository_url
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
