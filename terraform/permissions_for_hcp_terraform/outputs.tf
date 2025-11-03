output hcp_terraform_infrastructure_organization {
  description = "The HCP Terraform organization where the infrastructure workspace is located."
  value       = local.hcp_terraform_infrastructure_organization
}

output hcp_terraform_infrastructure_workspace_name {
  description = "The name of the HCP Terraform workspace that is used to create the infrastructure."
  value       = local.hcp_terraform_infrastructure_workspace_name
}

output hcp_terraform_role_arn {
  description = "The ARN of the IAM role that the HCP Terraform infrastructure workspace can assume to create resources."
  value       = aws_iam_role.hcp_terraform_role.arn
}
