variable ingestion_ecr_repo_name {
  description = "Name for the ingestion ECR repository"
  type        = string
}

variable github_repo {
  description = "GitHub repository in the format 'owner/repo'"
  type        = string
}

variable github_role_name {
  description = "Name for the GitHub Actions IAM role"
  type        = string
}

variable github_role_path {
  description = "Path for the GitHub Actions IAM role"
  type        = string
}

variable movies_s3_bucket_name {
  description = "Name for the S3 bucket to store movie data"
  type        = string
}

variable ingestion_lambda_role_name {
  description = "Name for the IAM role that the ingestion Lambda function will assume"
  type        = string
}

variable ingestion_lambda_role_path {
  description = "Path for the IAM role that the ingestion Lambda function will assume"
  type        = string
}

variable ingestion_lambda_function_name {
  description = "Name for the ingestion Lambda function"
  type        = string
}

variable region {
  description = "The AWS region"
  type        = string
}

variable ingestion_lambda_memory_size {
  description = "Memory size for the ingestion Lambda function"
  type        = number
}

variable ingestion_lambda_timeout {
  description = "Timeout for the ingestion Lambda function"
  type        = number
}

variable ingestion_event_rule_name {
  description = "Name for the EventBridge rule that will trigger the ingestion Lambda function"
  type        = string
}

variable ingestion_event_schedule_expression {
  description = "Schedule expression for the EventBridge rule that will trigger the ingestion Lambda function"
  type        = string
}

variable pg_database {
  description = "Name of the PostgreSQL database"
  type        = string
}

variable pg_user {
  description = "Username for the PostgreSQL database"
  type        = string
}

variable pg_password {
  description = "Password for the PostgreSQL database"
  type        = string
  sensitive   = true
}
