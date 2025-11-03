terraform {
  cloud {
    organization = "movies"
    workspaces {
      name = "permissions_for_hcp_terraform"
    }
  }
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.92"
    }
  }

  required_version = ">= 1.2"
}

# Define which workspace is used to create the infrastructure. That will be
# allowed to assume a role with necessary permissions.
locals {
  hcp_terraform_infrastructure_organization   = "movies"
  hcp_terraform_infrastructure_project        = "movies_project"
  hcp_terraform_infrastructure_workspace_name = "infrastructure"
}
