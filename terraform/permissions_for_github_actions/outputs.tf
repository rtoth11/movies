output github_actions_role_for_infrastructure_arn {
  description = "The ARN of the IAM role that Github Actions can assume to create resources."
  value       = aws_iam_role.github_actions_role.arn
}
