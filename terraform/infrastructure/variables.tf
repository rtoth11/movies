variable extraction_ecr_repo_name {
  description = "Name for the ECR repository that will store the extraction image"
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

variable pg_export_ecr_repo_name {
  description = "Name for the ECR repository that will store the pg-export image"
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

variable extraction_ec2_role_name {
  description = "Name for the IAM role that the extraction EC2 instance will assume"
  type        = string
}

variable extraction_ec2_role_path {
  description = "Path for the IAM role that the extraction EC2 instance will assume"
  type        = string
}

variable extraction_event_bridge_role_name {
  description = "Name for the IAM role that the EventBridge rule will assume to start the extraction EC2 instance"
  type        = string
}

variable region {
  description = "The AWS region"
  type        = string
}

variable extraction_event_rule_name {
  description = "Name for the EventBridge rule that will start the extraction EC2 instance"
  type        = string
}

variable extraction_event_schedule_expression {
  description = "Schedule expression for the EventBridge rule that will start the extraction EC2 instance"
  type        = string
}

variable pg_database {
  description = "Name of the PostgreSQL database"
  type        = string
}

variable pg_user {
  description = "Username for the PostgreSQL database"
  type        = string
  sensitive   = true
}

variable pg_password {
  description = "Password for the PostgreSQL database"
  type        = string
  sensitive   = true
}

variable "deploy_backend_and_frontend" {
  description = "Flag to enable or disable the deployment of backend and frontend services"
  type        = bool
  default     = false
}

variable "ec2_ami" {
  description = "The AMI of the image to use for EC2 instances"
  type        = string
}

variable "ec2_instance_type" {
  description = "The instance type of the EC2 instances to create"
  type        = string
}

variable "my_ip_cidr" {
  type        = string
  description = "Your public IP in CIDR notation (e.g. 203.0.113.42/32). It is allowed to access the PostgreSQL database."
}
