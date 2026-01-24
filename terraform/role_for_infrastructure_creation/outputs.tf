output role_for_infrastructure_creation {
  description = "The ARN of the IAM role that can be assumed to create infrastructure via Terraform."
  value       = aws_iam_role.role_for_infrastructure_creation.arn
}
