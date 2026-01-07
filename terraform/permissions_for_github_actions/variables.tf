variable region {
  description = "AWS region"
  type        = string
}

variable github_repo {
  description = "GitHub repository in the format 'owner/repo'"
  type        = string
}

variable github_role_name {
  description = "Name for the Github Actions IAM role used to create infrastructure"
  type        = string
}

variable github_role_path {
  description = "Path for the Github Actions IAM role used to create infrastructure"
  type        = string
}
