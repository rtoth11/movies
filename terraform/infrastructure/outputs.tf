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
