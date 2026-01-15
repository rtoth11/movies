terraform {
  cloud {
    organization = "movies"
    workspaces {
      name = "permissions_for_github_actions"
    }
  }
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.28"
    }
  }

  required_version = ">= 1.2"
}
