variable extraction_ecr_repo_name {
  description = "Name for the ECR repository that will store the extraction Lambda function image"
  type        = string
}

variable backend_ecr_repo_name {
  description = "Name for the ECR repository that will store the backend service image"
  type        = string
}

variable frontend_ecr_repo_name {
  description = "Name for the ECR repository that will store the frontend service image"
  type        = string
}

variable github_repo {
  description = "GitHub repository in the format 'owner/repo'. This can assume the role with necessary permissions to update infrastructure."
  type        = string
}

variable name_of_role_for_infrastructure_update {
  description = "Name for the role that can be assumed to update infrastructure"
  type        = string
}

variable path_of_role_for_infrastructure_update {
  description = "Path for the role that can be assumed to update infrastructure"
  type        = string
}

variable movies_s3_bucket_name {
  description = "Name for the S3 bucket to store movie data"
  type        = string
}

variable extraction_lambda_role_name {
  description = "Name for the IAM role that the extraction Lambda function will assume"
  type        = string
}

variable extraction_lambda_role_path {
  description = "Path for the IAM role that the extraction Lambda function will assume"
  type        = string
}

variable extraction_lambda_function_name {
  description = "Name for the extraction Lambda function"
  type        = string
}

variable region {
  description = "The AWS region"
  type        = string
}

variable extraction_lambda_memory_size {
  description = "Memory size for the extraction Lambda function"
  type        = number
}

variable extraction_lambda_timeout {
  description = "Timeout for the extraction Lambda function"
  type        = number
}

variable extraction_event_rule_name {
  description = "Name for the EventBridge rule that will trigger the extraction Lambda function"
  type        = string
}

variable extraction_event_schedule_expression {
  description = "Schedule expression for the EventBridge rule that will trigger the extraction Lambda function"
  type        = string
}

variable pg_database {
  description = "Name of the PostgreSQL database"
  type        = string
}

variable pg_user {
  description = "Username for the PostgreSQL database"
  type        = string
  sensitive = true
}

variable pg_password {
  description = "Password for the PostgreSQL database"
  type        = string
  sensitive   = true
}

variable "backend_cpu" {
  description = "CPU units for the backend ECS task"
  type        = number
}

variable "backend_memory" {
  description = "Memory (in MiB) for the backend ECS task"
  type        = number
}

variable "frontend_cpu" {
  description = "CPU units for the frontend ECS task"
  type        = number
}

variable "frontend_memory" {
  description = "Memory (in MiB) for the frontend ECS task"
  type        = number
}

variable "deploy_backend_and_frontend" {
  description = "Flag to enable or disable the deployment of backend and frontend services"
  type        = bool
  default     = false
}
